FROM python:latest
MAINTAINER Ryan Kortmann "ryankortmann@gmail.com"

# Packages
ADD docker/packages.txt /tmp/packages.txt
RUN apt-get update -y
RUN cat /tmp/packages.txt | xargs apt-get install -y

# PIP
ADD docker/pip.txt /tmp/pip.txt
RUN pip install --upgrade pip
RUN pip install -r /tmp/pip.txt

# Set the timezone.
RUN echo "America/New_York" > /etc/timezone
RUN dpkg-reconfigure -f noninteractive tzdata

# Add an unprivileged user for celery's worker
RUN adduser --disabled-password --gecos '' worker

# Start server
WORKDIR /var/gspotsyncer/
EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]