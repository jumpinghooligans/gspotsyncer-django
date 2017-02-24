#!/bin/sh

# wait for PSQL server to start
sleep 5

su -m worker -c "celery worker -A gspotsyncer.celery -Q default -n default@%h"