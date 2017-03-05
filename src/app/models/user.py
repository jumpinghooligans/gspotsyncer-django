import requests, base64

from django.db import models, IntegrityError
from django.conf import settings
from django.utils import http
from django.contrib.auth.models import User
from django.contrib.postgres import fields
from django.dispatch import receiver
from django.db.models import signals

from apiclient.discovery import build
from oauth2client.contrib import xsrfutil
from oauth2client.contrib.django_util.models import CredentialsField
from oauth2client.contrib.django_util.storage import DjangoORMStorage
from oauth2client.client import OAuth2WebServerFlow

from app.models.core import AppModel
from app.api.google import GoogleApi
from app.api.spotify import SpotifyApi
from app.api.youtube import YoutubeApi
from app.models.playlist import GooglePlaylist, SpotifyPlaylist, YoutubePlaylist

import logging
logger = logging.getLogger('consolelog')

class Profile(AppModel):
    # link to User model
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    def refresh_external_playlists(self, refresh_tracks = False):
        logger.info('Profile refresh_external_playlists')

        # Google Music
        try:
            self.user.googleprofile.refresh_external_playlists(refresh_tracks)

        except GoogleProfile.DoesNotExist:
            pass

        # Spotify
        try:
            self.user.spotifyprofile.refresh_external_playlists(refresh_tracks)

        except SpotifyProfile.DoesNotExist:
            pass

        # Youtube
        try:
            self.user.youtubeprofile.refresh_external_playlists(refresh_tracks)

        except YoutubeProfile.DoesNotExist:
            pass

        return True

# On User create, create a blank profile
@receiver(signals.post_save, sender=User)
def create_blank_profile(sender, instance, created, **kwargs):
    if created:
        new_profile = Profile(user=instance)
        new_profile.save()


class GoogleProfile(AppModel):
    # link to User model
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    # Google profile data
    username = models.CharField(max_length=255)
    password = models.CharField(max_length=255)

    def refresh_external_playlists(self, refresh_tracks = False):

        logger.info('GoogleProfile refresh_external_playlists')

        api = GoogleApi(self.user)

        external_playlists = api.get_full_playlists()

        for playlist in external_playlists:

            # create a new playlist
            new_playlist = GooglePlaylist(user=self.user)

            # parse the data
            new_playlist.parse(playlist)

            # save it or update it
            try:
                new_playlist.save()

                # set this as the working playlist
                working_playlist = new_playlist

            except IntegrityError:
                # pull the existing one from the db
                existing_playlist = GooglePlaylist.objects.get(service='gm', service_id=new_playlist.service_id)

                # update with our variable values
                existing_playlist.parse_variable_data(playlist)

                # save!
                existing_playlist.save()

                # set this as the working playlist
                working_playlist = existing_playlist

            if refresh_tracks:
                working_playlist.refresh_tracks()

    def disconnect(self):

        # nice and simple
        return self.delete()

class SpotifyProfile(AppModel):
    # link to User model
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    # Schema
    token_type = models.CharField(max_length=255)

    # What we really need
    access_token = models.CharField(max_length=500)
    refresh_token = models.CharField(max_length=500)

    # Not really useful
    scope = models.CharField(max_length=500)
    expires_in = models.IntegerField()

    # JSON blob of Spotify user data
    spotify_user = fields.JSONField(null=True)

    def refresh_external_playlists(self, refresh_tracks = False):

        logger.info('SpotifyProfile refresh_external_playlists')

        api = SpotifyApi(self.user)

        external_playlists = api.get_playlists()

        for playlist in external_playlists:

            # create a new playlist
            new_playlist = SpotifyPlaylist(user=self.user)

            # parse the data
            new_playlist.parse(playlist)

            # save it or update it
            try:
                new_playlist.save()

                # set this as the working playlist
                working_playlist = new_playlist

            except IntegrityError:
                # pull the existing one from the db
                existing_playlist = SpotifyPlaylist.objects.get(service='sp', service_id=new_playlist.service_id)

                # update with our variable values
                existing_playlist.parse_variable_data(playlist)

                # save!
                existing_playlist.save()

                # set this as the working playlist
                working_playlist = existing_playlist

            if refresh_tracks:
                working_playlist.refresh_tracks()

    def get_token(self, request):

        # Make the request for an access token
        spotify_auth_response = requests.post(
            url='https://accounts.spotify.com/api/token',
            headers={ 'Authorization' : 'Basic ' + self.get_encoded_auth() },
            data={
                'grant_type' : 'authorization_code',
                'code' : request.GET.get('code'),
                'redirect_uri' : self.return_url(request)
            }
        )

        # make sure we get a valid response
        if spotify_auth_response.status_code == requests.codes.ok:

            # update our credentials
            credential_data = spotify_auth_response.json()

            # set our data
            self.token_type = credential_data.get('token_type')
            self.access_token = credential_data.get('access_token')
            self.refresh_token = credential_data.get('refresh_token')
            self.scope = credential_data.get('scope')
            self.expires_in = credential_data.get('expires_in')

            # update spotify user
            self.refresh_user()

            self.save()
            return True

        return False

    def refresh_access_token(self):
        refresh_response = requests.post(
            url='https://accounts.spotify.com/api/token',
            headers={ 'Authorization' : 'Basic ' + self.get_encoded_auth() },
            data={
                'grant_type' : 'refresh_token',
                'refresh_token' : self.refresh_token
            }
        )

        # make sure we get a valid response
        if refresh_response.status_code == requests.codes.ok:
            credential_data = refresh_response.json()

            logger.info(credential_data)

            # update our credentials
            self.token_type = credential_data.get('token_type')
            self.access_token = credential_data.get('access_token')
            self.scope = credential_data.get('scope')
            self.expires_in = credential_data.get('expires_in')

            # refresh the spotify user
            self.refresh_user()

            self.save()
            return True
        
        return False

    def disconnect(self):

        # nice and simple
        return self.delete()

    def refresh_user(self):
        # init the API
        spotify = SpotifyApi(self.user)

        # grab the data
        spotify_data = spotify.get_me()

        # save it
        if spotify_data:
            self.spotify_user = spotify_data
            return True

        return False

    # The URL we redirect them to to validate their
    # spotify credentials and get us a token
    def connect_url(self, request):
        scope = " ".join([
            'playlist-read-private',
            'playlist-read-collaborative',
            'playlist-modify-public',
            'playlist-modify-private',
        ])

        params = {
            'response_type' : 'code',
            'client_id' : settings.SPOTIFY_CLIENT_ID,
            'scope' : scope,
            'redirect_uri' : self.return_url(request)
        }

        return 'https://accounts.spotify.com/authorize?' + http.urlencode(params)

    def return_url(self, request):
        return 'http://' + request.get_host() + '/account/spotify/return'

    def get_encoded_auth(self):
        auth_string = settings.SPOTIFY_CLIENT_ID + ':' + settings.SPOTIFY_CLIENT_SECRET
        return base64.b64encode(auth_string.encode()).decode()

class YoutubeProfile(AppModel):
    # link to User model
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    # Special Google API credential field
    credentials = CredentialsField()

    def refresh_external_playlists(self, refresh_tracks = False):

        logger.info('YoutubeProfile refresh_external_playlists')

        api = YoutubeApi(self.user)

        external_playlists = api.get_playlists()

        for playlist in external_playlists:

            # create a new playlist
            new_playlist = YoutubePlaylist(user=self.user)

            # parse the data
            new_playlist.parse(playlist)

            # save it or update it
            try:
                new_playlist.save()

                # set this as the working playlist
                working_playlist = new_playlist

            except IntegrityError:
                # pull the existing one from the db
                existing_playlist = YoutubePlaylist.objects.get(service='yt', service_id=new_playlist.service_id)

                # update with our variable values
                existing_playlist.parse_variable_data(playlist)

                # save!
                existing_playlist.save()

                # set this as the working playlist
                working_playlist = existing_playlist

            if refresh_tracks:
                working_playlist.refresh_tracks()

    def get_credentials(self):

        # get the storage object
        storage = DjangoORMStorage(YoutubeProfile, 'user', self.user, 'credentials')

        credentials = storage.get()

        logger.info(credentials.invalid)

        return credentials


    def connect(self, flow, code):

        credentials = flow.step2_exchange(code)

        storage = DjangoORMStorage(YoutubeProfile, 'user', self.user, 'credentials')

        storage.put(credentials)

        return True

    def disconnect(self):

        # nice and simple
        return self.delete()

    # The URL we redirect them to to validate their
    # youtube credentials and get us a token
    def connect_url(self, flow):

        return flow.step1_get_authorize_url()

    def get_flow(self, request):

        return OAuth2WebServerFlow(
            client_id=settings.GOOGLE_OAUTH2_CLIENT_ID,
            client_secret=settings.GOOGLE_OAUTH2_CLIENT_SECRET,
            scope='https://www.googleapis.com/auth/youtube',
            redirect_uri=self.return_url(request)
        )
    
    def return_url(self, request):
        return 'http://' + request.get_host() + '/account/youtube/return'