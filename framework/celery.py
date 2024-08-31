
from __future__ import absolute_import, unicode_literals # for python2

import os
from celery import Celery

# set the default Django settings module for the 'celery' program.
# this is also used in manage.py
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'framework.settings')


## Get the base REDIS URL, default to redis' default
BASE_REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379')

app = Celery('framework')

# Using a string here means the worker don't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()

app.conf.broker_url = BASE_REDIS_URL

# this allows you to schedule items in the Django admin.
app.conf.beat_scheduler = 'django_celery_beat.schedulers.DatabaseScheduler'


app.conf.beat_schedule = {
    'check_inactive_worker_in_every_6_minutes': {
        'task': 'unassign_moderator_from_inactive_workers',  
        'schedule': 360.0
    },
    'check_inactive_worker_in_every_minute': {
        'task': 'assign_moderator_from_inactive_to_active_workers',
        'schedule': 60.0

    },
    'reminder_for_unread_messages_in_every_10_minutes': {
        'task': 'reminder_for_unread_messages',
        'schedule': 60.0

    }
}