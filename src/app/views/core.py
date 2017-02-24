from django.shortcuts import render
from django.http import HttpResponse
from django.contrib import messages

from app.models.playlist import Playlist
from app.models.spotify import SpotifyApi
from app.models.track import Track

from worker import tasks

import logging
logger = logging.getLogger(__name__)

def index(request):
    return render(request, 'core/index.j2')

def test(request):
	track = Track.objects.get(pk=610)

	# track.name = 'asdf'
	track.discover()

	return HttpResponse(track.name)