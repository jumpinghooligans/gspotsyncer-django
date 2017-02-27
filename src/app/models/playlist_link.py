from django.db import models

from app.models.core import AppModel
from app.models.user import User

import logging
logger = logging.getLogger('consolelog')

class PlaylistLink(AppModel):
    # User can have many Playlists
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    source = models.ForeignKey('Playlist', related_name='source_playlist_id', on_delete=models.CASCADE)
    destination = models.ForeignKey('Playlist', related_name='destination_playlist_id', on_delete=models.CASCADE)

    def sources(self):

    	source_playlists = []
    	
    	all_sources = PlaylistLink.objects.filter(
    		user = self.user,
    		destination = self.destination
    	)

    	for source in all_sources:
    		source_playlists.append(source.source)

    	return source_playlists

    class Meta:
        unique_together = ('user', 'destination')