from apiclient.discovery import build

from oauth2client.contrib.django_util.storage import DjangoORMStorage

import logging, httplib2

logger = logging.getLogger('consolelog')

class YoutubeApi():

    def __init__(self, user):
        # shouldn't need this
        self.user = user

        # should just use this
        self.api = None
        if hasattr(user, 'youtubeprofile') and hasattr(user.youtubeprofile, 'credentials'):

            credentials = user.youtubeprofile.get_credentials()

            self.api = build('youtube', 'v3', http=credentials.authorize(httplib2.Http()))

    def get_playlists(self):

        playlists = self.api.playlists().list(
            part='id,snippet',
            mine=True,
            maxResults=50
        ).execute()

        return playlists.get('items', [])

    def playlist_add(self, playlist_id, track_ids):

        for track_id in track_ids:

            data = {
                'snippet' : {
                    'playlistId' : playlist_id,
                    'resourceId' : {
                        'kind' : 'youtube#video',
                        'videoId' : track_id
                    }
                }
            }

            logger.info('Insert on: ' + str(data))

            result = self.api.playlistItems().insert(
                part = "id,snippet",
                body = data,
            ).execute()


    def playlist_clear(self, playlist_id):

        playlist_items_req = self.api.playlistItems().list(
            playlistId=playlist_id,
            part="id",
            maxResults=50
        )

        while playlist_items_req:

            playlist_items = playlist_items_req.execute()

            for playlist_item in playlist_items.get('items', []):

                # get the item ID
                self.api.playlistItems().delete(
                    id=playlist_item.get('id')
                ).execute()

            playlist_items_req = self.api.playlistItems().list_next(
                playlist_items_req,
                playlist_items
            )

    def search_songs(self, query):

        return self.search(query)

    def search(self, query):

        search_results = self.api.search().list(
            q=query,
            part="id,snippet",
            maxResults=5,
            type='video',
        ).execute()

        return search_results.get('items', [])
