from django import forms
from django.db import IntegrityError
from django.shortcuts import render, redirect
from django.core import serializers
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required

from app.models.spotify import SpotifyApi
from app.models.google import GoogleApi

from app.models.playlist import Playlist
from app.models.playlist_link import PlaylistLink

import logging, json
logger = logging.getLogger('consolelog')

@login_required
def index(request):

    user = request.user

    # Get the playlist links linked to this user
    parent_playlist_links = user.playlistlink_set.all().distinct('destination')

    for link in parent_playlist_links:
        logger.info(link.sources())    

    return HttpResponse(parent_playlist_links)

@login_required
def create(request):

    user = request.user

    if request.method == 'POST':

        # Get our destination track
        destination = request.POST.get('destination')

        # Verify it and get the object
        try:
            destination = Playlist.objects.get(pk=destination)

        except Playlist.DoesNotExist:
            messages.add_message(request, messages.ERROR, 'Invalid destination playlist')

            # try again
            return redirect('/playlists/create')


        # Get all our source tracks
        sources = request.POST.getlist('source')

        # Verify it and get the objects
        try:
            source_objects = []

            for source in sources:
                source_objects.append(Playlist.objects.get(pk=source))

        except Playlist.DoesNotExist:
            messages.add_message(request, messages.ERROR, 'Invalid source playlist')

            # try again
            return redirect('/playlists/create')


        # create a playlist link for each source
        for source in source_objects:

            try:

                PlaylistLink(
                    user = user,
                    source = source,
                    destination = destination
                ).save()

            except IntegrityError:
                pass

        return redirect('/account')

    # make sure our playlist data is up to date
    # user.profile.refresh_external_playlists()

    # playlists registered with spotify
    spotify_playlists = user.playlist_set.filter(service='sp')

    # playlists registered with google music
    google_playlists = user.playlist_set.filter(service='gm')

    services = [
        {
            'id' : 'gm',
            'name' : 'Google Music'
        },
        {
            'id' : 'sp',
            'name' : 'Spotify'
        }
    ]

    return render(request, 'playlist/create.j2', {
        'spotify_playlists' : serializers.serialize('json', spotify_playlists),
        'google_playlists' : serializers.serialize('json', google_playlists),
        'services' : services
    })