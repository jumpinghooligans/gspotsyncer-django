from django.contrib import admin

from .models.user import Profile, GoogleProfile, SpotifyProfile
from .models.playlist import Playlist
from .models.playlist_link import PlaylistLink
from .models.track import Track, TrackLink, SpotifyTrack, GoogleTrack

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

@admin.register(PlaylistLink)
class PlaylistLinkAdmin(AppModelAdmin):
    pass


# Show service tracks on the track
class SpotifyTrackAdminInline(admin.TabularInline):
    model = SpotifyTrack

class GoogleTrackAdminInline(admin.TabularInline):
    model = GoogleTrack

@admin.register(Track)
class TrackAdmin(AppModelAdmin):
    list_display = ('name', 'artist',)
    inlines = (SpotifyTrackAdminInline, GoogleTrackAdminInline,)

@admin.register(TrackLink)
class TrackLinkAdmin(AppModelAdmin):
    list_display = ('track', 'playlist', 'status',)

@admin.register(SpotifyTrack)
class SpotifyTrackAdmin(AppModelAdmin):
    list_display = ('track', 'spotify_id', 'uri',)

@admin.register(GoogleTrack)
class GoogleTrackAdmin(AppModelAdmin):
    pass


# for fun
admin.site.site_header = 'gspotsyncer admin'