from django.db import models
from gmusicapi import Mobileclient

class GoogleApi(models.Model):

    def __init__(self, user):
        # we'll probably need this later
        self.user = user

        # store our creds
        self.googleprofile = user.googleprofile

        # hold the API
        self.api = False

    def init(self):

        if self.api:
            return self.api

        # init the API
        api = Mobileclient()

        # make sure we have
        if not hasattr(self.googleprofile, 'username'):
            return False

        # what we need
        if not hasattr(self.googleprofile, 'password'):
            return False

        # attempt login
        logged_in = api.login(self.googleprofile.username, self.googleprofile.password, api.FROM_MAC_ADDRESS)

        if logged_in:
            self.api = api
            return self.api

        return False

    def get_playlists(self):

        api = self.init()

        playlists = []

        if api:
            playlists = api.get_all_playlists()

        return playlists

    def get_full_playlists(self):
        api = self.init()
        playlists = []

        if api:
            playlists = api.get_all_user_playlist_contents()

        return playlists

    # todo
    def get_playlist_tracks(self, playlist_id):
        pass

    # don't create a table n' shit
    class Meta:
        managed = False

# class GoogleTrack(models.Model):