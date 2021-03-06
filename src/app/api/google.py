from gmusicapi import Mobileclient

import logging, time
logger = logging.getLogger('consolelog')

class GoogleApi():

    def __init__(self, user):
        # we'll probably need this later
        self.user = user

        # store our creds
        self.googleprofile = user.googleprofile

        # hold the API
        self.api = False

    def init(self, retry = True):

        # if we have a good api object, return that
        if self.api and self.api.is_authenticated():
            return self.api

        # init the API
        api = Mobileclient()

        # make sure we have
        if not hasattr(self.googleprofile, 'username'):
            return False

        # what we need
        if not hasattr(self.googleprofile, 'password'):
            return False

        # attempt login (sometimes we gate rate limited)
        refresh_attempts = 10
        current_attempt = 1
        refresh_seed = 3

        while refresh_attempts > 0:

            # attempt a login
            logged_in = api.login(self.googleprofile.username, self.googleprofile.password, api.FROM_MAC_ADDRESS)

            # break out if we are either:
            #  - successful
            #  - don't want to retry
            if logged_in or not retry:
                logger.error('Successfully logged into Google Music')
                break

            else:
                refresh_delay = refresh_seed ** current_attempt

                logger.error('Failed to authenticate, sleeping for ' + str(refresh_delay) + ' seconds (attempt ' + str(current_attempt) + ')')
                time.sleep(refresh_delay)
                refresh_attempts -= 1
                current_attempt += 1

        if logged_in:
            self.api = api
            return self.api

        logger.error('Slept ' + str(current_attempt) + ' times for ' + str(refresh_delay) + ' seconds, still failed')

        return False

    def get_playlists(self):

        api = self.init()

        playlists = []

        if api:
            playlists = api.get_all_playlists()

        return playlists

    def get_full_playlists(self):
        api = self.init()
        playlists = []

        if api:
            playlists = api.get_all_user_playlist_contents()

        return playlists


    def playlist_remove(self, delete_nids):

        api = self.init()

        if api:
            result = api.remove_entries_from_playlist(delete_nids)

            logger.info('Google Playlist Remove result: ' + str(result))

            return result

        return False

    def playlist_add(self, playlist_id, insert_ids):

        api = self.init()

        if api:
            result = api.add_songs_to_playlist(playlist_id, insert_ids)

            logger.info('Google Playlist Add result: ' + str(result))

            return result

        return False

    def search_songs(self, query):
        logger.info('Searching Google Music for song: ' + query)

        songs = []
        full_results = self.search(query)

        return full_results.get('song_hits', [])

    def search(self, query):

        api = self.init()
        results = {}

        if api:
            results = api.search(query)

        return results

    # todo
    def get_playlist_tracks(self, playlist_id):
        pass

    # don't create a table n' shit
    class Meta:
        managed = False

# class GoogleTrack(models.Model):