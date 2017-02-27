from django.contrib import admin

from .models.user import Profile, GoogleProfile, SpotifyProfile
from .models.playlist import Playlist
from .models.playlist_link import PlaylistLink
from .models.track import Track, TrackLink, SpotifyTrack, GoogleTrack

import logging
logger = logging.getLogger('consolelog')

class AppModelAdmin(admin.ModelAdmin):
    def __init__(self, model, admin_site):
        if self.list_display == ('__str__',):
            self.list_display = ('id',) + self.list_display

        self.list_display += ('modified_date', 'created_date',)

        if self.readonly_fields == ():
            self.readonly_fields = ('id',)

        self.readonly_fields += ('modified_date', 'created_date',)

        super(AppModelAdmin, self).__init__(model, admin_site)


@admin.register(Profile)
class ProfileAdmin(AppModelAdmin):
    list_display = ('user',)
    actions = ['refresh_playlists']

    def refresh_playlists(self, request, queryset):
        logger.info('ProfileAdmin refresh_playlists')

        for user_profile in queryset:
            user_profile.refresh_external_playlists()

    refresh_playlists.short_description = 'Refresh user playlists'

@admin.register(GoogleProfile)
class GoogleProfileAdmin(AppModelAdmin):
    list_display = ('username','user',)

@admin.register(SpotifyProfile)
class SpotifyProfileAdmin(AppModelAdmin):
    list_display = ('user',)


@admin.register(Playlist)
class PlaylistAdmin(AppModelAdmin):
    list_display = ('name', 'user', 'service',)
    readonly_fields = ('proxy_class',)
    actions = ['refresh_tracks']

    # refresh tracks
    def refresh_tracks(self, request, queryset):
        logger.info('PlaylistAdmin refresh_tracks')

        for playlist in queryset:
            playlist.refresh_tracks()

    refresh_tracks.short_description = 'Refresh playlist tracks'

@admin.register(PlaylistLink)
class PlaylistLinkAdmin(AppModelAdmin):
    list_display = ('id', 'user', 'source', 'destination',)


# Show service tracks on the track
class SpotifyTrackAdminInline(admin.TabularInline):
    model = SpotifyTrack
    extra = 0

class GoogleTrackAdminInline(admin.TabularInline):
    model = GoogleTrack
    extra = 0

@admin.register(Track)
class TrackAdmin(AppModelAdmin):
    search_fields = ['name', 'artist', 'album',]
    list_display = ('name', 'artist',)
    inlines = (SpotifyTrackAdminInline, GoogleTrackAdminInline,)
    actions = ['rediscover',]

    # rediscover service links
    def rediscover(self, request, queryset):
        logger.info('TrackAdmin rediscover')

        for track in queryset:
            logger.info('rediscover with ' + str(track.pk))
            track.discover()

    rediscover.short_description = 'Rediscover track'

@admin.register(TrackLink)
class TrackLinkAdmin(AppModelAdmin):
    list_display = ('track', 'playlist', 'status',)

@admin.register(SpotifyTrack)
class SpotifyTrackAdmin(AppModelAdmin):
    search_fields = ['track__name', 'track__artist', 'spotify_id',]
    list_display = ('track', 'spotify_id', 'uri',)

@admin.register(GoogleTrack)
class GoogleTrackAdmin(AppModelAdmin):
    search_fields = ['track__name', 'track__artist', 'google_id',]
    pass


# for fun
admin.site.site_header = 'gspotsyncer admin'