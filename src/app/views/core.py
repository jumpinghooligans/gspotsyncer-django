from django.shortcuts import render
from django.http import HttpResponse
from django.contrib import messages

from app.models.playlist import Playlist
from app.models.spotify import SpotifyApi

import logging
logger = logging.getLogger(__name__)

def index(request):
    return render(request, 'core/index.j2')

def test(request):
	
	request.user.userprofile.refresh_external_playlists()

	return HttpResponse('meh')