from django.db import models
from django.contrib.postgres import fields

from app.models.core import AppModel
from app.models.user import User

import logging
logger = logging.getLogger(__name__)

class Track(AppModel):
    name = models.CharField(max_length=500)
    artist = models.CharField(max_length=500, null=True)
    album = models.CharField(max_length=500, null=True)

    album_image = models.CharField(max_length=1000, null=True)

    # 'discovering' a track is a two part process
    #  - check our local tracks for an exact match
    #  - using the service API, search for the best match
    def discover(self):
        matching_tracks = Track.objects.filter(
            name = self.name,
            artist = self.artist,
            album = self.album
        ).exclude(
            pk = self.pk
        ).distinct()

        logger.error(matching_tracks)

        for matching_track in matching_tracks:

            # if this track has spotify and we don't, attach it
            if hasattr(matching_track, 'spotifytrack') and not hasattr(self, 'spotifytrack'):
                self.spotifytrack = matching_track.spotifytrack

            # if this track has google and we don't, attach it
            if hasattr(matching_track, 'googletrack') and not hasattr(self, 'googletrack'):
                self.googletrack = matching_track.googletrack

            # save the updates
            self.save()

            # todo: handle other links :/
            matching_track.delete()

            # nothing else to do
            return True

        return False

    class Meta:
        ordering = ['tracklink__order',]

    def __str__(self):
        return self.name

# Many to many relationship between Playlists and tracks
class TrackLink(AppModel):
    track = models.ForeignKey('Track')
    playlist = models.ForeignKey('Playlist')

    order = models.PositiveIntegerField()
    status = models.CharField(max_length=255)

    class Meta:
        ordering = ['order',]

# These are extension models not subclasses
class SpotifyTrack(AppModel):
    # base track
    track = models.OneToOneField('Track', on_delete=models.CASCADE)

    # if there is a user id, we should use that, manuel override
    user = models.ForeignKey(User, null=True, on_delete=models.CASCADE)

    # easy lookup to see if we already have the track
    spotify_id = models.CharField(max_length=255, unique=True)
    uri = models.CharField(max_length=255, unique=True)

    # i'm lazy, just dump the rest of the track data here
    track_data = fields.JSONField(null=True)
    
    def parse(self, track_data):
        track = track_data.get('track')

        self.spotify_id = track.get('id')
        self.uri = track.get('uri')
        
        self.track_data = track_data

    def generate_base_track(self):
        track_data = self.track_data
        track = track_data.get('track')

        new_track = Track()

        new_track.name = track.get('name')
        new_track.status = 'live'

        artists = track.get('artists')

        if artists and len(artists) > 0:
            new_track.artist = artists[0].get('name')

        album = track.get('album')

        if album:
            new_track.album = album.get('name')
            new_track.album_image = album.get('images')[0].get('url')

        return new_track

class GoogleTrack(AppModel):
    # base track
    track = models.OneToOneField('Track', on_delete=models.CASCADE)

    # if there is a user id, we should use that, manuel override
    user = models.ForeignKey(User, null=True, on_delete=models.CASCADE)

    google_id = models.CharField(max_length=255, unique=True)
    nid = models.CharField(max_length=255, unique=True)

    # i'm lazy, just dump the rest of the track data here
    track_data = fields.JSONField(null=True)
    
    def parse(self, track_data):
        track = track_data.get('track', {})

        self.google_id = track_data.get('id')
        self.nid = track.get('nid')
        
        self.track_data = track_data

    def generate_base_track(self):
        track_data = self.track_data
        track = track_data.get('track')

        new_track = Track()

        new_track.name = track.get('title')
        new_track.status = 'live'
        new_track.artist = track.get('artist')
        new_track.album = track.get('album')

        album_art_ref = track.get('albumArtRef')

        if album_art_ref and len(album_art_ref) > 0:
            new_track.album_image = album_art_ref[0].get('url')

        return new_track