#!/bin/sh

# wait for PSQL server to start
sleep 10

celery --app=gspotsyncer.celery:app worker --loglevel=INFO