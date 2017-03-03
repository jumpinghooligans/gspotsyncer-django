import requests, json

from django.db import models

import logging
logger = logging.getLogger('consolelog')

class SpotifyApi(models.Model):

	def __init__(self, user):
		# shouldn't need this
		self.user = user

		# should just use this
		self.profile = None
		if hasattr(user, 'spotifyprofile'):
			self.profile = user.spotifyprofile

	# Refresh Spotify's user data
	# 
	# Store it on the SpotifyProfile.spotify_user
	def get_me(self):

		# pull updated data from Spotify
		return self.request('get',
			url='https://api.spotify.com/v1/me'
		)

	def get_playlists(self):
		res = self.request('get',
			url='https://api.spotify.com/v1/me/playlists'
		)

		# return the items property
		if res:
			return res.get('items', [])

		return []

	def get_playlist_tracks(self, owner_id, playlist_id):
		res = self.request('get',
			url='https://api.spotify.com/v1/users/' + owner_id +'/playlists/' + playlist_id
		)

		if res:
			return res.get('tracks', {}).get('items', [])

		return []


	def playlist_remove(self, owner_id, playlist_id, delete_uris):
		logger.info('Removing ' + str(delete_uris) + ' from ' + playlist_id)

		uris = []
		for delete_uri in delete_uris:
			uris.append({
				'uri' : delete_uri
			})

		data = {
			'tracks' : uris
		}

		res = self.request('delete',
			url='https://api.spotify.com/v1/users/' + owner_id +'/playlists/' + playlist_id + '/tracks',
			headers={ 'Content-Type' : 'application/json' },
			data=json.dumps(data)
		)

		if res:
			logger.info('Spotify playlist remove result: ' + str(res))
			return True

		return False

	def playlist_add(self, owner_id, playlist_id, insert_ids):
		logger.info('Adding ' + str(insert_ids) + ' from ' + playlist_id)

		data = {
			'uris' : insert_ids
		}

		res = self.request('post',
			url='https://api.spotify.com/v1/users/' + owner_id +'/playlists/' + playlist_id + '/tracks',
			headers={ 'Content-Type' : 'application/json' },
			data=json.dumps(data)
		)

		if res:
			logger.info('Spotify playlist add result: ' + str(res))
			return True

		return False

	def search_songs(self, query):
		logger.info('Searching for Spotify song: ' + query)

		search_results = self.search(query, 'track')

		if not search_results:
			return []

		search_results = search_results.get('tracks', {})
		search_results = search_results.get('items', [])

		return search_results

	def search(self, query, result_type):
		params = {
			'q' : query,
			'type' : result_type
		}

		return self.request('get',
			url='https://api.spotify.com/v1/search',
			params=params
		)

	# A generic request function for making API calls
	# 
	# This will handle authorization for most spotify requests
	def request(self, verb, **kwargs):

		# We need credentials to make any requests
		if not self.profile:
			return False

		# GET or POST
		requester = getattr(requests, verb)

		# attach the user credentials
		if not kwargs.get('headers', None):
			kwargs['headers'] = {}

		kwargs['headers'].update({ 'Authorization' : self.profile.token_type + ' ' + self.profile.access_token })

		# hacky way of making sure we don't loop on 401s
		refresh_attempted = getattr(self, 'refresh_attempted', False)

		# make the request
		res = requester(**kwargs)

		# if we get a 401 - attempt a refresh
		if res.status_code == 401 and not refresh_attempted:
			logger.info("User " + str(self.user.username) + " Received 401 - Refreshing Token")

			# Don't get stuck in a unauthorized loop
			self.refresh_attempted = True

			if self.profile.refresh_access_token():
				# update the kwargs
				kwargs['headers'] = { 'Authorization' : self.profile.token_type + ' ' + self.profile.access_token }

				# try this request again
				return self.request(verb, **kwargs)
			else:
				logger.info('refresh failed')
				# we tried to refresh but failed, there's probably
				# some real issue, return the original request
				self.profile.disconnect()

				try:
					return res.json()

				except ValueError:
					return False
		else:
			# request is not a 401 - pass on through
			self.refresh_attempted = False

			try:
				return res.json()

			except ValueError:
				return False

	# don't create a table n' shit
	class Meta:
		abstract = True
