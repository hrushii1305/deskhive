web: python manage.py migrate && python manage.py collectstatic --noinput && gunicorn deskhive.wsgi
worker: celery -A deskhive worker --loglevel=info
beat: celery -A deskhive beat --loglevel=info