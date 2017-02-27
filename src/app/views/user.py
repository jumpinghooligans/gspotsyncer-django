import requests

from django import forms
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm

# Model classes
from app.models.user import User, GoogleProfile, SpotifyProfile
from app.models.google import GoogleApi
from app.models.spotify import SpotifyApi

from django.http import HttpResponse

import logging
logger = logging.getLogger('consolelog')

#
# ROUTES
#

def create(request):

    # Create a new user
    if request.method == 'POST':
        form = UserCreationForm(request.POST)

        if form.is_valid():
            # get the form data
            username, password = form.cleaned_data['username'], form.cleaned_data['password1']

            # create the user
            new_user = User.objects.create_user(username, None, password)
            new_user.is_active = True
            new_user.save()

            # log them in
            login(request, new_user)

            # bounce them to their account
            return redirect('/account')

    else:
        form = UserCreationForm()

    return render(request, 'user/create.j2', { 'form' : form })

# General account info
@login_required
def account(request):

    # Autobuild a related model form
    GoogleProfileForm = forms.inlineformset_factory(User, GoogleProfile, fields=('username', 'password',), can_delete=False)

    # Render the forms for this user
    google_form = GoogleProfileForm(instance=request.user)
    user_form = ModifyForm(instance=request.user, label_suffix='')

    return render(request, 'user/account.j2', { 
        'user_form' : user_form,
        'google_form' : google_form,
    })

# Account modifications
# 
# username/password
@login_required
def modify(request):

    # Update google credentials
    if request.method == 'POST':

        # Get the POST data
        user_updates = ModifyForm(request.POST, instance=request.user)

        if user_updates.is_valid():
            # Save and redirect (refresh)
            user_updates.save()

    return redirect('/account')

# Refresh the user's playlists
@login_required
def refresh_playlists(request):

    # reach out to the services and refresh the playlists
    request.user.profile.refresh_external_playlists()


# Currently just responds to the google credentials
# form submit on the account page
@login_required
def google_connect(request):

    # Build a related model form
    GoogleProfileForm = forms.inlineformset_factory(User, GoogleProfile, fields=('username', 'password',), can_delete=False)

    # Update google credentials
    if request.method == 'POST':
        # Get the POST data
        google_form = GoogleProfileForm(request.POST, instance=request.user)

        if google_form.is_valid():
            # There isn't anything to register against like spotify
            # so really we just make sure the creds work and thats it
            google_form.save()

            # init google api to test the input
            google = GoogleApi(request.user)

            # make sure the user/pass validates
            # False means, don't use rate limiting re-attempts
            valid = google.init(False)

            if valid:
                # All good
                messages.add_message(request, messages.INFO, 'Connected Google Music')
            else:
                # remove the profile relation (it's not right)
                request.user.googleprofile.delete()
                messages.add_message(request, messages.ERROR, 'Failed to connect Google Music')

    return redirect('/account')

# Deletes the Google Profile record for this user
@login_required
def google_disconnect(request):

    # Delete if it exists
    if request.user.googleprofile:
        request.user.googleprofile.disconnect()

    return redirect('/account')

# Connect a spotify account
@login_required
def spotify_connect(request):

    # shoot them off to the Spotify auth
    spotify_profile = SpotifyProfile(user=request.user)
    return redirect(spotify_profile.connect_url(request))

# Return URL for spotify, this is where we actually
# link the account
@login_required
def spotify_return(request):

    # successful if we get a 'code' query param
    if request.GET.get('code'):

        # create a new profile
        spotify_profile = SpotifyProfile(user=request.user)

        # using the code, get an api token (and refresh our user info)
        if spotify_profile.get_token(request):
            messages.add_message(request, messages.INFO, 'Succesfully linked your Spotify account!')

        else:
            messages.add_message(request, messages.ERROR, 'Something went wrong...')

    else:

        # in theory there should be an error
        messages.add_message(request, messages.ERROR, request.GET.get('error', 'Something went wrong...'))

    return redirect('/account')

# Disconnect the user and delete the data we have
@login_required
def spotify_disconnect(request):

    # Delete if it exists
    if request.user.spotifyprofile:
        request.user.spotifyprofile.disconnect()

    return redirect('/account')

#
# FORMS
#

class ModifyForm(forms.ModelForm):

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'username']