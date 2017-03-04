from django.shortcuts import render
from django.http import HttpResponse
from django.contrib import messages

from app.models.playlist import Playlist
from app.api.youtube import YoutubeApi
from app.models.track import Track

from worker import tasks

import logging
logger = logging.getLogger('consolelog')

def index(request):
    return render(request, 'core/index.j2')

def test(request):

	api = YoutubeApi(request.user)

	return HttpResponse(api.search_songs('kanye west ultra light beam'))