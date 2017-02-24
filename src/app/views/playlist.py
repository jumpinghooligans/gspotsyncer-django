from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required

from app.models.spotify import SpotifyApi
from app.models.google import GoogleApi

import logging
logger = logging.getLogger(__name__)

@login_required
def create(request):

    user = request.user
    
    # make sure our playlist data is up to date
    user.profile.refresh_external_playlists(True)

    # playlists registered with spotify
    spotify_playlists = user.playlist_set.filter(service='sp')

    # playlists registered with google music
    google_playlists = user.playlist_set.filter(service='gm')

    return render(request, 'playlist/create.j2', {
        'spotify_playlists' : spotify_playlists,
        'google_playlists' : google_playlists,
    })