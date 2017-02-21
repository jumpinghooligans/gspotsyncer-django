from django.conf.urls import url
from django.contrib.auth import views as user_auth

from .views import core, user, track, playlist

urlpatterns = [
	# Core pages (index/about/contact)
    url(r'^$', core.index),

    # User Account
    url(r'^account/$', user.account),

    # User Create
    url(r'^account/create/$', user.create),

    # User modify (username/password)
    url(r'^account/modify/$', user.modify),

    # User Login
    url(r'^login/$', user_auth.login, {'template_name': 'user/login.j2'}, name='login'),
    url(r'^account/login/$', user_auth.login, {'template_name': 'user/login.j2'}, name='login'),

    # User Logout
    url(r'^logout/$', user_auth.logout, {'next_page': '/'}, name='logout'),
    url(r'^account/logout/$', user_auth.logout, {'next_page': '/'}, name='logout'),

    # User Google Profile
    url(r'^account/google/connect/$', user.google_connect),
    url(r'^account/google/disconnect/$', user.google_disconnect),

    # User Spotify Profile
    url(r'^account/spotify/connect/$', user.spotify_connect),
    url(r'^account/spotify/return/$', user.spotify_return),
    url(r'^account/spotify/disconnect/$', user.spotify_disconnect),

    # Playlist Create
    url(r'^playlists/create', playlist.create),

    url(r'^test/$', core.test)
]