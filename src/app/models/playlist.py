from django.db import models
from django.contrib.postgres import fields
from django.conf import settings

from app.models.core import AppModel
from app.models.user import User
from app.models.playlist_link import PlaylistLink

from app.models.track import Track, TrackLink, SpotifyTrack, GoogleTrack

from app.models.google import GoogleApi
from app.models.spotify import SpotifyApi

import logging
logger = logging.getLogger('consolelog')

class Playlist(AppModel):

    # User can have many Playlists
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    # Schema
    name = models.CharField(max_length=255)

    # where does this playlist belong
    service = models.CharField(
        max_length=2,
        choices=settings.SERVICES
    )
    # how to get more data
    service_id = models.CharField(max_length=255)

    # other
    url = models.CharField(max_length=500)
    owner_id = models.CharField(max_length=255)
    raw = fields.JSONField(null=True)

    # track links
    tracks = models.ManyToManyField('Track', through=TrackLink)

    proxy_class = models.CharField(max_length=255)

    #
    # Some fuckery I found here: http://schinckel.net/2013/07/28/django-single-table-inheritance-on-the-cheap./
    #
    # Essentially this will force items returned to be the proxy subclass
    #  - This allows me to keep one table
    #  - This allows me to seperate code into different models
    #
    def __init__(self, *args, **kwargs):
        super(Playlist, self).__init__(*args, **kwargs)

        # If we don't have a subclass at all, then we need the
        # type attribute to match our current class. 
        if not self.__class__.__subclasses__():
            self.proxy_class = self.__class__.__name__.lower()

        else:
            subclass = [x for x in self.__class__.__subclasses__() if x.__name__.lower() == self.proxy_class]

            if subclass:
                self.__class__ = subclass[0]

            else:
                self.proxy_class = self.__class__.__name__.lower()

    def __str__(self):
         return self.name + " (" + self.service + ")"

    class Meta:
        unique_together = ('service', 'service_id',)

class GooglePlaylist(Playlist):

    # This is a proxy model, mostly just for me to separate
    # different services code, it all saves to the base Playlist
    class Meta:
        proxy = True

    # Take a Google Music playlist JSON object
    # and parse it into a Playlist
    def parse(self, playlist_data):
        self.parse_final_data(playlist_data)
        self.parse_variable_data(playlist_data)

    # This data will be frozen
    def parse_final_data(self, playlist_data):
        self.service = 'gm'
        self.service_id = playlist_data.get('id')

    # This data will be updated every refresh
    def parse_variable_data(self, playlist_data):
        self.name = playlist_data.get('name')
        self.owner_id = playlist_data.get('ownerName')
        self.raw = playlist_data

    def get_tracks():
        return self.tracks.all()

    def get_raw_tracks(self):
        # pull out the tracks dict
        return self.raw.get('tracks', [])

    # create or update 
    def refresh_tracks(self):

        logger.info('GooglePlaylist refresh_tracks triggered')

        # google music playlists have the tracks stored right
        # on the playlist
        tracks = self.get_raw_tracks()
        
        # blow away the existing track links
        self.tracks.clear()

        track_idx = 1
        for track in tracks:

            # create a new instance
            google_track = GoogleTrack()

            # set the data
            google_track.parse(track)

            # skip tracks that don't have a nid, these were
            # user uploads, and they can't be linked :(
            if not google_track.nid:
                continue

            # check if this track for this service already exists
            try:
                # this track exists
                google_track = GoogleTrack.objects.get(nid=google_track.nid)
                logger.info('GoogleTrack exists')

                # pull out the base track
                base_track = google_track.track

                # do any updating we would need

            except GoogleTrack.DoesNotExist:
                # this track doesn't exist, we need to create it
                # (base track first)
                base_track = google_track.generate_base_track()
                base_track.added_by = self.user
                base_track.save()

                # associate with our new base track
                google_track.track = base_track
                google_track.save()

                logger.info('GoogleTrack created')

            # Create a track link
            track_link = TrackLink(
                playlist = self,
                track = base_track,
                order = track_idx
            ).save()

            # increment (python doesn't do ++ ... ?)
            track_idx += 1

class SpotifyPlaylist(Playlist):

    # This is a proxy model, mostly just for me to separate
    # different services code, it all saves to the base Playlist
    class Meta:
        proxy = True

    # Take a Spotify playlist JSON object
    # and parse it into a Playlist
    def parse(self, playlist_data):
        self.parse_final_data(playlist_data)
        self.parse_variable_data(playlist_data)

    # This data will be frozen
    def parse_final_data(self, playlist_data):
        self.service = 'sp'
        self.service_id = playlist_data.get('id')

    # This data will be updated every refresh
    def parse_variable_data(self, playlist_data):
        self.name = playlist_data.get('name')
        self.url = playlist_data.get('href')
        self.owner_id = playlist_data.get('owner', {}).get('id')
        self.raw = playlist_data

    # create or update 
    def refresh_tracks(self):

        logger.info('SpotifyPlaylist refresh_tracks triggered')

        api = SpotifyApi(self.user)

        tracks = api.get_playlist_tracks(self.owner_id, self.service_id)

        if not tracks:
            return False
        
        # blow away the existing track links
        self.tracks.clear()

        track_idx = 1
        for track in tracks:

            # create a new instance
            spotify_track = SpotifyTrack()

            # set the data
            spotify_track.parse(track)

            # skip tracks that don't have a spotify_id, these were
            # user uploads, and they can't be linked :(
            if not spotify_track.spotify_id:
                continue

            # check if this track for this service already exists
            try:
                # this track exists
                spotify_track = SpotifyTrack.objects.get(spotify_id=spotify_track.spotify_id)
                logger.info('SpotifyTrack exists')

                # pull out the base track
                base_track = spotify_track.track

                # do any updating we would need

            except SpotifyTrack.DoesNotExist:
                # this track doesn't exist, we need to create it
                # (base track first)
                base_track = spotify_track.generate_base_track()
                base_track.added_by = self.user
                base_track.save()

                # associate with our new base track
                spotify_track.track = base_track
                spotify_track.save()

                logger.info('SpotifyTrack created')

            # Create a track link
            track_link = TrackLink(
                playlist = self,
                track = base_track,
                order = track_idx
            ).save()

            # increment (python doesn't do ++ ... ?)
            track_idx += 1
