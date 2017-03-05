#!/bin/sh

# wait for PSQL server to start
sleep 10

echo $APP_ENV

if [ "$APP_ENV" = "DEV" ]
	then
		python manage.py runserver 0.0.0.0:8000
	else
		gunicorn --bind 0.0.0.0:8000 gspotsyncer.wsgi:application
fi