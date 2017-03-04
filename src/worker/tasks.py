# Worker tasks
from __future__ import absolute_import
from celery import shared_task

from django.dispatch import receiver
from django.db.models import signals

from app.models.track import Track

import logging
logger = logging.getLogger('consolelog')

# When a new track is created, trigger an async track to discover
# it's service tracks
@receiver(signals.post_save, sender='app.Track')
def trigger_discover_track(sender, instance, created, **kwargs):

    if created and instance.added_by:

        discover_track.delay(instance.pk)

# Actual task to run (100 per minute)
# rate_limit='100/m'
@shared_task(rate_limit='20/m')
def discover_track(track_id):

    try:
        track = Track.objects.get(pk=track_id)

    except Track.DoesNotExist:
        return 'Track to discover has been deleted (probably merged)'

    logger.info('Discover track ' + track.name + ' (' + str(track.id) + ')')

    result = track.discover()

    return 'Discover result: ' + str(result)