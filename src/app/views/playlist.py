from django import forms
from django.db import IntegrityError
from django.shortcuts import render, redirect
from django.core import serializers
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required

from app.models.spotify import SpotifyApi
from app.models.google import GoogleApi

from app.models.playlist import Playlist, PlaylistLink

import logging, json
logger = logging.getLogger('consolelog')

@login_required
def index(request):

    user = request.user

    # Get the playlist links linked to this user
    playlist_links = request.user.playlistlink_set.all();

    # Format each one
    formatted_links = []

    for playlist_link in playlist_links:

        # serialize these
        formatted_links.append(playlist_link.serialize())

    return render(request, 'playlist/index.j2', {
        'playlist_links' : formatted_links
    })

@login_required
def read(request, playlist_id = None):
    return HttpResponse(playlist_id)

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


        # Create the playlist link object
        new_link = PlaylistLink(
            user = user,
            destination = destination
        )

        new_link.save()

        # add each source
        for source in source_objects:
            new_link.sources.add(source)

        try:
            new_link.save()

        except IntegrityError:
            return HttpResponse('IntegrityError')

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