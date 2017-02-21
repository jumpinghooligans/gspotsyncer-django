from django.db import models

from app.models.core import AppModel
from app.models.user import User

import logging
logger = logging.getLogger(__name__)

class PlaylistLink(AppModel):
    # User can have many Playlists
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    source = models.ForeignKey('Playlist', related_name='source_playlist_id', on_delete=models.CASCADE)
    destination = models.ForeignKey('Playlist', related_name='destination_playlist_id', on_delete=models.CASCADE)

    class Meta:
        unique_together = ('user', 'destination')