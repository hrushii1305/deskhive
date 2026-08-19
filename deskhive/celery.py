import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deskhive.settings')

app = Celery('deskhive')                                    # ← app created first
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

app.conf.beat_schedule = {                                  # ← then configured
    'escalate-stale-tickets': {
        'task': 'tickets.tasks.escalate_stale_tickets',
        'schedule': crontab(minute=0),
    },
}