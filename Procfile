web: python manage.py migrate && python manage.py collectstatic --noinput && daphne -b 0.0.0.0 -p $PORT deskhive.asgi:application
worker: celery -A deskhive worker --loglevel=info
beat: celery -A deskhive beat --loglevel=info