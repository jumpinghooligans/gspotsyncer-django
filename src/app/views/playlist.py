from django import forms
from django.db import IntegrityError
from django.shortcuts import render, redirect
from django.core import serializers
from django.contrib import messages
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required

from app.api.spotify import SpotifyApi
from app.api.google import GoogleApi

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
        'playlist_links' : json.dumps(formatted_links)
    })


@login_required
def publish(request, playlist_link_id = None):

    user = request.user

    playlist_link = user.playlistlink_set.get(pk=playlist_link_id)

    playlist_link.publish_draft()

    return redirect('/playlists/' + playlist_link_id)

@login_required
def read(request, playlist_link_id = None):

    user = request.user

    if request.method == 'POST':
        pass

    playlist_link = user.playlistlink_set.get(pk=playlist_link_id)

    return render(request, 'playlist/read.j2', {
        'playlist_link' : json.dumps(playlist_link.serialize(True))
    })

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

        try:
            new_link.save()

            # add each source
            for source in source_objects:

                new_link.sources.add(source)

            # build out our new draft
            new_link.build_draft()

            return redirect('/playlists/' + str(new_link.pk))

        except IntegrityError:
            
            messages.add_message(request, messages.ERROR, 'The selected destination playlist is already in use')

            return redirect('/playlists/create')

        return redirect('/account')

    # make sure our playlist data is up to date
    # user.profile.refresh_external_playlists()

    # playlists registered with spotify
    spotify_playlists = user.playlist_set.filter(service='sp')

    # playlists registered with google music
    google_playlists = user.playlist_set.filter(service='gm')

    # playlists registered with google music
    youtube_playlists = user.playlist_set.filter(service='yt')

    # services we can write to
    destination_services = [
        {
            'id' : 'gm',
            'name' : 'Google Music'
        },
        {
            'id' : 'sp',
            'name' : 'Spotify'
        },
        {
            'id' : 'yt',
            'name' : 'YouTube'
        }
    ]

    # services we can read from (not youtube)
    source_services = [
        {
            'id' : 'gm',
            'name' : 'Google Music'
        },
        {
            'id' : 'sp',
            'name' : 'Spotify'
        },
    ]

    return render(request, 'playlist/create.j2', {
        'spotify_playlists' : serializers.serialize('json', spotify_playlists),
        'google_playlists' : serializers.serialize('json', google_playlists),
        'youtube_playlists' : serializers.serialize('json', youtube_playlists),
        'destination_services' : destination_services,
        'source_services' : source_services
    })
