# Worker tasks
from __future__ import absolute_import
from celery import shared_task

from django.dispatch import receiver
from django.db.models import signals

from app.models.track import Track

@shared_task
def test(param):
    return 'The test task executed with argument "%s" ' % param


# When a new track is created, trigger an async track to discover
# it's service tracks
@receiver(signals.post_save, sender='app.Track')
def trigger_discover_track(sender, instance, created, **kwargs):
    # if created:
	discover_track.delay(instance.pk)

# Actual task to run
@shared_task
def discover_track(track_id):

	track = Track.objects.get(pk=track_id)

	result = track.discover()

	return 'discoverr track ' + str(track_id)