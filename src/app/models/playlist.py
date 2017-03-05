from datetime import datetime

from django.db import models
from django.forms.models import model_to_dict
from django.contrib.postgres import fields
from django.conf import settings
from django.core import serializers

from app.models.core import AppModel
from app.models.user import User

from app.models.track import Track, TrackLink, SpotifyTrack, GoogleTrack

from app.api.google import GoogleApi
from app.api.spotify import SpotifyApi
from app.api.youtube import YoutubeApi

import logging, random
logger = logging.getLogger('consolelog')

class Playlist(AppModel):

    # User can have many Playlists
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    # Schema
    name = models.CharField(max_length=255)

    # where does this playlist belong
    service = models.CharField(
        max_length=2,
        choices=settings.SERVICE_CHOICES
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


    # simple for now
    def serialize(self, include_tracks = False):
        tracks = self.tracks.all()

        # pick a random track and grab its album image
        random_album_art = self.get_random_album_art(tracks)

        # get base playlist
        playlist = {
            'pk' : self.pk,
            'name' : self.name,
            'user' : self.user.username,
            'service' : self.service,
            'service_id' : self.service_id,
            'url' : self.url,
            'owner_id' : self.owner_id,
            'random_album_art' : random_album_art or '',
            'live_tracks' : [],
            'draft_tracks' : [],
        }

        if include_tracks:

            # Man python and passing data to the front end is ... interesting
            for track in tracks.filter(tracklink__status='live').order_by('tracklink__order'):

                # Add a serialized track
                playlist.get('live_tracks').append(track.serialize())

            # Man python and passing data to the front end is ... interesting
            for track in tracks.filter(tracklink__status='draft').order_by('tracklink__order'):

                # Add a serialized track
                playlist.get('draft_tracks').append(track.serialize())

        return playlist

    def get_random_album_art(self, tracks = None):

        if not tracks:

            tracks = self.tracks.all()

        random_album_art = None

        if tracks.count() > 0:

            random_album_art = tracks[ random.randint(0, (tracks.count() - 1)) ].album_image

        return random_album_art

    def __str__(self):
         return self.name + " (" + self.service + ")"

    class Meta:
        unique_together = ('service', 'service_id',)

class PlaylistLink(AppModel):
    # User can have many Playlists
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    # single destination
    destination = models.OneToOneField('Playlist', related_name='destination_playlist_id')

    # many sources
    sources = models.ManyToManyField('Playlist')

    # shortcut
    random_album_art = models.CharField(max_length=500, null=True)

    # timestamps
    refreshed = models.DateTimeField(null=True)
    published = models.DateTimeField(null=True)

    # publish any tracklinks marked as draft
    def publish_draft(self):
        # for safety, refresh external tracks of destination
        self.destination.refresh_tracks(True)

        # get our track ids
        live_track_ids = self.destination.get_service_track_ids('live')
        draft_track_ids = self.destination.get_service_track_ids('draft')

        # delete, whats live and not in our draft list
        delete_ids = list(set(live_track_ids) - set(draft_track_ids))

        # insert whats in our draft list and not live
        insert_ids = list(set(draft_track_ids) - set(live_track_ids))

        # reorder insert ids
        order_insert_ids = [ o for o in draft_track_ids if o in insert_ids]

        logger.info('tracks to insert: ' + str(order_insert_ids))
        logger.info('tracks to delete: ' + str(delete_ids))

        # hit the service and delete what we need to
        self.destination.remove_tracks(delete_ids)

        # then add anything new
        self.destination.add_tracks(order_insert_ids)

        # for safety, refresh external tracks of destination
        self.destination.refresh_tracks(True)

        self.published = datetime.now()

    # build a set of draft links
    def build_draft(self):

        # first refresh what we have live
        self.destination.refresh_tracks(True)

        # clear out any current draft track links
        self.destination.tracklink_set.filter(status='draft').delete()

        # for now just loop through each source playlist
        # and add that draft track
        running_order = 1
        for source_playlist in self.sources.all():

            # for safety, refresh each source
            # 
            # HACK ALERT: since google needs a FULL playlist
            # refresh to do this, i'm only running it on
            # the first loop
            source_playlist.refresh_tracks((running_order == 1))

            # create a tracklink for each track in every
            # playlist we're linked to
            for track in source_playlist.tracks.all():

                logger.info('Creating draft TrackLink for: ' + str(track))
                TrackLink(
                    playlist = self.destination,
                    track = track,
                    order = running_order,
                    status = 'draft'
                ).save()

                running_order += 1

        self.refreshed = datetime.now()

    # build a serializeable playlist link object
    def serialize(self, include_tracks = False):

        playlist_link = {}

        # playlist link data
        playlist_link['pk'] = self.pk

        # destination playlist
        playlist_link['destination'] = self.destination.serialize(include_tracks)

        # source playlists
        playlist_link['sources'] = []

        # format each source playlist
        for source in self.sources.all():

            playlist_link['sources'].append(source.serialize())

        # grab an image from the first source playlist
        self.refresh_random_album_art()
        playlist_link['random_album_art'] = self.random_album_art

        return playlist_link

    def refresh_random_album_art(self):

        source = self.sources.first()

        self.random_album_art = source.get_random_album_art()

        self.save(update_fields=['random_album_art'])


    class Meta:
        unique_together = ('user', 'destination')

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

    def get_service_track_ids(self, status):
        
        service_track_ids = []

        for track in self.tracks.filter(tracklink__status=status).order_by('tracklink__order'):

            # gonna have to change this later
            google_track = track.get_google_track()

            if google_track:

                service_track_ids.append(google_track.google_id)

        return service_track_ids

    def add_tracks(self, track_ids):

        api = GoogleApi(self.user)

        playlist_id = self.service_id

        return api.playlist_add(playlist_id, track_ids)

    def remove_tracks(self, track_ids):

        api = GoogleApi(self.user)

        # we need to translate these
        entry_ids = self.get_entry_ids(track_ids)

        return api.playlist_remove(entry_ids)

    def get_entry_ids(self, track_ids):
        
        entry_ids = []

        for track in self.tracks.filter(googletrack__google_id__in=track_ids):

            # wonky but get the entry id of this track
            # for this playlist
            track_links = track.tracklink_set.filter(
                playlist=self,
                status='live'
            )

            if track_links:

                for track_link in track_links:

                    entry_ids.append(track_link.entry_id)

        return entry_ids

    def get_tracks():
        # actually get them from the DB
        return self.tracks.all()

    def get_raw_tracks(self):
        # pull out the tracks dict
        return self.raw.get('tracks', [])

    # create or update 
    def refresh_tracks(self, refresh_playlists = False):

        logger.info('GooglePlaylist refresh_tracks triggered')

        # google is a pain, you have to refresh ALL playlists
        # just to get one track list
        if refresh_playlists:
            self.user.googleprofile.refresh_external_playlists()

        # google music playlists have the tracks stored right
        # on the playlist
        tracks = self.get_raw_tracks()
        
        # blow away the existing track links
        self.tracklink_set.filter(status='live').delete()

        track_idx = 1
        for track in tracks:

            # each playlist entry has a uid
            entry_id = track.get('id')

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
                google_track = GoogleTrack.objects.get(google_id=google_track.google_id)
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
            TrackLink(
                playlist = self,
                track = base_track,
                order = track_idx,
                status = 'live',
                entry_id = entry_id
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
        self.owner_id = playlist_data.get('owner', {}).get('id')

        self.url = playlist_data.get('href')

        album_images = playlist_data.get('album', {}).get('images', [])

        self.raw = playlist_data

    def get_service_track_ids(self, status):
        
        service_track_ids = []

        for track in self.tracks.filter(tracklink__status=status).order_by('tracklink__order'):

            # gonna have to change this later
            spotify_track = track.get_spotify_track()

            if spotify_track:

                service_track_ids.append(spotify_track.uri)

        return service_track_ids

    def add_tracks(self, track_ids):

        api = SpotifyApi(self.user)

        owner_id = self.owner_id
        playlist_id = self.service_id

        return api.playlist_add(owner_id, playlist_id, track_ids)

    def remove_tracks(self, track_ids):

        api = SpotifyApi(self.user)

        owner_id = self.owner_id
        playlist_id = self.service_id

        return api.playlist_remove(owner_id, playlist_id, track_ids)

    # create or update 
    def refresh_tracks(self, refresh_playlists = False):

        logger.info('SpotifyPlaylist refresh_tracks triggered')

        api = SpotifyApi(self.user)

        tracks = api.get_playlist_tracks(self.owner_id, self.service_id)
        
        # blow away the existing track links
        self.tracklink_set.filter(status='live').delete()

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
            TrackLink(
                playlist = self,
                track = base_track,
                order = track_idx,
                status = 'live'
            ).save()

            # increment (python doesn't do ++ ... ?)
            track_idx += 1

class YoutubePlaylist(Playlist):

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
        self.service = 'yt'
        self.service_id = playlist_data.get('id')

    # This data will be updated every refresh
    def parse_variable_data(self, playlist_data):
        snippet = playlist_data.get('snippet', {})

        self.name = snippet.get('title')

        self.raw = playlist_data

    def get_service_track_ids(self, status):
        
        service_track_ids = []

        for track in self.tracks.filter(tracklink__status=status).order_by('tracklink__order'):

            # gonna have to change this later
            youtube_track = track.get_youtube_track()

            if youtube_track:

                service_track_ids.append(youtube_track.youtube_id)

        return service_track_ids

    def add_tracks(self, track_ids):
        api = YoutubeApi(self.user)

        playlist_id = self.service_id

        return api.playlist_add(playlist_id, track_ids)

    # remove errything - ignore specific tracks
    # for now
    def remove_tracks(self, track_ids):

        api = YoutubeApi(self.user)

        playlist_id = self.service_id

        api.playlist_clear(playlist_id)

    # this doesn't really work since we don't have sufficient
    # metadata to parse tracks, so right now youtube is 
    # write only (clear it out and rewrite)
    def refresh_tracks(self, refresh_playlists = False):
        pass