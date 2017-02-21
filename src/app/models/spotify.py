import requests

from django.db import models

import logging
logger = logging.getLogger(__name__)

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
		res = self.request('get',
			url='https://api.spotify.com/v1/me'
		)

		# return the data if we got a response
		if res:
			return res.json()

		return False

	def get_playlists(self):
		res = self.request('get',
			url='https://api.spotify.com/v1/me/playlists'
		)

		# return the items property
		if res:
			res = res.json()
			return res.get('items', [])

		return False

	def get_playlist_tracks(self, owner_id, playlist_id):
		res = self.request('get',
			url='https://api.spotify.com/v1/users/' + owner_id +'/playlists/' + playlist_id
		)

		if res:
			res = res.json()
			return res.get('tracks', {}).get('items', [])

		return False

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

				logger.error('refresh access token passed')

				# try this request again
				return self.request(verb, **kwargs)
			else:
				logger.error('refresh failed')
				# we tried to refresh but failed, there's probably
				# some real issue, return the original request
				self.profile.disconnect()
				return res
		else:
			# request is not a 401 - pass on through
			self.refresh_attempted = False
			return res

	# don't create a table n' shit
	class Meta:
		abstract = True
