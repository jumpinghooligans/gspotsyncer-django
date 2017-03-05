#!/bin/sh

# wait for PSQL server to start
sleep 10

# python manage.py runserver 0.0.0.0:8000
gunicorn --bind 0.0.0.0:8000 gspotsyncer.wsgi:application