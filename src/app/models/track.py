import re

from django.db import models, IntegrityError
from django.contrib.postgres import fields
from django.conf import settings
from django.core import serializers

from app.models.core import AppModel
from app.models.user import User

from app.api.google import GoogleApi
from app.api.spotify import SpotifyApi
from app.api.youtube import YoutubeApi

import logging
logger = logging.getLogger('consolelog')

class Track(AppModel):
    name = models.CharField(max_length=500)
    artist = models.CharField(max_length=500, null=True)
    album = models.CharField(max_length=500, null=True)

    album_image = models.CharField(max_length=1000, null=True)

    # we need user credentials to do discovery, will probably have a system
    # fallback but...
    added_by = models.ForeignKey(User, null=True, default=None, on_delete=models.SET_DEFAULT)

    # 'discovering' a track is a two part process
    #  - check our local tracks for an exact match
    #  - using the service API, search for the best match
    def discover(self):

        # whether or not to move on to the next
        # round of discovery
        found_match = False
        success = False

        # First check our already stored tracks, someone
        # else could have already added this track
        if not found_match:
            logger.info('Attempting to discover_service')

            found_match = self.discover_local()

        # No luck? Let's hit the service APIs and
        # search for the track
        if not found_match:
            logger.info('Attempting to discover_service')

            for service in settings.SERVICES:

                service_match = self.discover_service(service[0])
                found_match = (found_match and service_match)

        return found_match

    # This will search our local app_tracks
    # table for a matching song
    def discover_local(self):

        matching_tracks = Track.objects.filter(
            name__iexact = self.name,
            artist__iexact = self.artist,
            album__iexact = self.album
        ).exclude(
            pk = self.pk
        )

        for matching_track in matching_tracks:

            # Merge pretty much just checks that the new
            # track has a service track we don't
            # if we found a match, we are done here
            return self.merge(matching_track)

        return False

    # This will search the given services
    def discover_service(self, service, rediscover_existing = False):
        logger.info('Discover service on ' + service)

        api = False

        if service == 'gm':
            if not rediscover_existing and self.googletrack_set.count() > 0:
                logger.info('Track already has a matching GoogleTracks, skipping GM')
                return True

            api = GoogleApi(self.added_by)
            service_track = GoogleTrack()

        elif service == 'sp':
            if not rediscover_existing and self.spotifytrack_set.count() > 0:
                logger.info('Track already has a matching SpotifyTrack, skipping SP')
                return True

            api = SpotifyApi(self.added_by)
            service_track = SpotifyTrack()

        elif service == 'yt':
            if not rediscover_existing and self.youtubetrack_set.count() > 0:
                logger.info('Track already has a matching YoutubeTrack, skipping YT')
                return True

            api = YoutubeApi(self.added_by)
            service_track = YoutubeTrack()

        # hit the correct service API and pull
        # some matching tracks
        matching_tracks = self.search(api)

        # Try to merge it
        for matching_track in matching_tracks:

            # dummy Track
            t = Track()

            # our new service track to merge
            service_track.parse(matching_track)

            # dummy Track to attach it to
            t = service_track.generate_base_track()
            t.save()

            logger.info('Created dummy track ' + str(t.pk))

            try:
                # attach it to our dummy track
                service_track.track = t

                service_track.save()

                logger.info('New service track saved, adding to parent Track set')

                # we just need it formatted correctly
                # hacky...
                if service == 'gm':
                    t.googletrack_set.add(service_track)

                elif service == 'sp':
                    t.spotifytrack_set.add(service_track)

                elif service == 'yt':
                    t.youtubetrack_set.add(service_track)

            except IntegrityError:
                logger.info('Unable to save new service_track due to IntegrityError')

                # if we can't create a new track, it already exists
                # let's merge our current self into that duplicate

                if service == 'gm':
                    dup_track = GoogleTrack.objects.get(google_id=service_track.google_id).track

                elif service == 'sp':
                    dup_track = SpotifyTrack.objects.get(spotify_id=service_track.spotify_id).track

                elif service == 'yt':
                    dup_track = YoutubeTrack.objects.get(youtube_id=service_track.youtube_id).track

                # merge and delete the dummy track we made
                logger.info('Found track ' + str(dup_track.pk) + ' with a linked service_track that caused the IntegrityError')
                logger.info('Attempting to merge current instance ' + str(self.pk) + ' with duplicate ' + str(dup_track.pk))

                logger.info('Clearing out dummy track ' + str(t.pk))
                t.delete()

                return dup_track.merge(self)

            # if we were able to create the service track
            # try to merge it in
            return self.merge(t)

        return False

    # This should take everything important from merge_track
    # and copy it over onto self
    def merge(self, merge_track):

        logger.info('Merge ' + str(merge_track.pk) + ' into ' + str(self.pk))

        valid_merge = False

        # can't merge into yourself
        if(self.pk == merge_track.pk):
            logger.info('Attempting to merge into self, skipping')
            return True

        # can't merge if you don't exist?
        try:
            self.refresh_from_db()

        except Track.DoesNotExist:
            logger.info('Attempting to merge into a track that does not exist, skipping')
            return True


        # Move over TrackLinks (linking tracks to playlists)
        try:
            logger.info('Attempting to move TrackLinks over')

            track_links = merge_track.tracklink_set.all()

            for track_link in track_links:

                # make sure we maintain playlists
                # that were attached to this track
                track_link.track = self

                track_link.save()


        except ValueError:
            pass

        # if this track has spotify track, attach it
        try:
            logger.info('Attempting to move SpotifyTracks over')

            for spotify_track in merge_track.spotifytrack_set.all():

                logger.info('Moving SpotifyTrack ' + str(spotify_track.pk) + ' from ' + str(merge_track.pk) + ' to ' + str(self.pk))

                # attach this track to our merge target
                spotify_track.track = self

                # save it
                spotify_track.save()

            # consider this a valid merge
            valid_merge = True

        except ValueError:
            logger.info('SpotifyTrack ValueError Exception in Merge')

        # if this track has google track, attach it
        try:
            logger.info('Attempting to move GoogleTracks over')

            for google_track in merge_track.googletrack_set.all():

                logger.info('Moving GoogleTrack ' + str(google_track.pk) + ' from ' + str(merge_track.pk) + ' to ' + str(self.pk))

                # attach this track to our merge target
                google_track.track = self

                # save it
                google_track.save()

            # consider this a valid merge
            valid_merge = True

        except ValueError:
            logger.info('GoogleTrack ValueError Exception in Merge')

        # if this track has google track, attach it
        try:
            logger.info('Attempting to move YoutubeTracks over')

            for youtube_track in merge_track.youtubetrack_set.all():

                logger.info('Moving GoogleTrack ' + str(youtube_track.pk) + ' from ' + str(merge_track.pk) + ' to ' + str(self.pk))

                # attach this track to our merge target
                youtube_track.track = self

                # save it
                youtube_track.save()

            # consider this a valid merge
            valid_merge = True

        except ValueError:
            logger.info('YoutubeTrack ValueError Exception in Merge')


        # If we were able to merge, we can save the track data
        if valid_merge and merge_track.id:
            # todo: handle other links :/
            #  - track links
            logger.info('Merge delete ' + str(merge_track.pk))
            merge_track.delete()

        return valid_merge

    def search(self, api):

        matching_tracks = []

        title = self.name
        primary_artist = self.artist
        album = self.album

        # start complex and get more basics
        queries = []

        # base query
        base_query = ' '.join(
            (title, primary_artist, album)
        ).encode('utf-8').strip().decode()

        # simpler base query
        simple_base_query = ' '.join(
            (title, primary_artist)
        ).encode('utf-8').strip().decode()

        # split on first paren (seems to work fairly well)
        part_paren = lambda x: x.partition('(')[0]
        part_dash = lambda x: x.partition('-')[0]

        split_paren_query = ' '.join(map(
            part_paren, (title, primary_artist, album)
        )).encode('utf-8').strip().decode()

        simple_split_paren_query = ' '.join(map(
            part_paren, (title, primary_artist)
        )).encode('utf-8').strip().decode()
        
        split_dash_query = ' '.join(map(
            part_dash, (title, primary_artist, album)
        )).encode('utf-8').strip().decode()

        simple_split_dash_query = ' '.join(map(
            part_dash, (title, primary_artist)
        )).encode('utf-8').strip().decode()

        # hacky, if this is youtube, just try a simple base query,
        # it seems to get really confused with specific searches
        if isinstance(api, YoutubeApi):

            logger.info('Youtube, only using simple query')

            queries.append(simple_base_query)

        else:
            # full query, then alpha numeric only
            queries.append(base_query)
            queries.append(re.sub(r'([^\s\w]|_)+', '', base_query))

            # simple query, then alpha numeric only
            queries.append(simple_base_query)
            queries.append(re.sub(r'([^\s\w]|_)+', '', simple_base_query))

            queries.append(split_paren_query)
            queries.append(simple_split_paren_query)
            
            queries.append(split_dash_query)
            queries.append(simple_split_dash_query)

        # should probably be checking search 'scores'
        # and doing some better sorting here
        for query in queries:

            logger.info('Querying: ' + query)

            matching_tracks += api.search_songs(query)

            if len(matching_tracks) > 0:
                logger.info('Found ' + str(len(matching_tracks)) + ' results - moving to next song')
                break

        return matching_tracks

    def serialize(self):
        return {
            'name' : self.name,
            'artist' : self.artist,
            'album' : self.album,
            'album_image' : self.album_image,
            'added_by' : self.added_by.username,
        }

    class Meta:
        pass
        # This is causing duplicates
        # ordering = ['tracklink__order',]

    def __str__(self):
        return self.name

# Many to many relationship between Playlists and tracks
class TrackLink(AppModel):
    track = models.ForeignKey('Track')
    playlist = models.ForeignKey('Playlist')

    order = models.PositiveIntegerField()
    status = models.CharField(max_length=255)

    # google uses entry id's rather than a
    # playlist id / track id combo
    entry_id = models.CharField(max_length=500, null=True)

    class Meta:
        ordering = ['order',]

# These are extension models not subclasses
class SpotifyTrack(AppModel):
    # base track
    track = models.ForeignKey('Track', on_delete=models.CASCADE)

    # service
    service = models.CharField(
        max_length=2,
        choices=settings.SERVICES,
        default='sp'
    )

    # if there is a user id, we should use that, manuel override
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE)

    # easy lookup to see if we already have the track
    spotify_id = models.CharField(max_length=255, unique=True)
    uri = models.CharField(max_length=255, unique=True)

    # i'm lazy, just dump the rest of the track data here
    track_data = fields.JSONField(null=True)
    
    def parse(self, track_data):

        logger.info('SpotifyTrack parse')

        track = track_data.get('track', track_data)

        self.spotify_id = track.get('id')
        self.uri = track.get('uri')
        
        self.track_data = track_data

    def generate_base_track(self):

        logger.info('SpotifyTrack generate_base_track')

        track_data = self.track_data
        track = track_data.get('track', track_data)

        new_track = Track()

        new_track.name = track.get('name')

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
    track = models.ForeignKey('Track', on_delete=models.CASCADE)

    # service
    service = models.CharField(
        max_length=2,
        choices=settings.SERVICES,
        default='gm'
    )

    # if there is a user id, we should use that, manuel override
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE)

    google_id = models.CharField(max_length=255, unique=True)
    nid = models.CharField(max_length=255, unique=True)

    # i'm lazy, just dump the rest of the track data here
    track_data = fields.JSONField(null=True)
    
    def parse(self, track_data):

        logger.info('GoogleTrack parse')

        track = track_data.get('track', {})

        self.google_id = track.get('storeId')
        self.nid = track.get('nid')
        
        self.track_data = track_data

    def generate_base_track(self):

        logger.info('GoogleTrack generate_base_track')

        track_data = self.track_data
        track = track_data.get('track')

        new_track = Track()

        new_track.name = track.get('title')
        new_track.artist = track.get('artist')
        new_track.album = track.get('album')

        album_art_ref = track.get('albumArtRef')

        if album_art_ref and len(album_art_ref) > 0:
            new_track.album_image = album_art_ref[0].get('url')

        return new_track

class YoutubeTrack(AppModel):
    # base track
    track = models.ForeignKey('Track', on_delete=models.CASCADE)

    # service
    service = models.CharField(
        max_length=2,
        choices=settings.SERVICES,
        default='yt'
    )

    # if there is a user id, we should use that, manuel override
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE)

    youtube_id = models.CharField(max_length=255, unique=True)

    # i'm lazy, just dump the rest of the track data here
    track_data = fields.JSONField(null=True)
    
    def parse(self, track_data):

        logger.info('YoutubeTrack parse')

        track = track_data.get('track', {})

        # could be a string
        youtube_id = track_data.get('id')

        # or nested (search result)
        # try:
        youtube_id = youtube_id.get('videoId', youtube_id)

        self.youtube_id = youtube_id
        
        self.track_data = track_data

    def generate_base_track(self):
        
        track_data = self.track_data
        snippet = track_data.get('snippet', {})

        new_track = Track()

        new_track.name = snippet.get('title')

        logger.info(new_track.name)

        return new_track