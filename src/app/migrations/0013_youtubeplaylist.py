# -*- coding: utf-8 -*-
# Generated by Django 1.10.6 on 2017-03-04 19:25
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0012_auto_20170304_1852'),
    ]

    operations = [
        migrations.CreateModel(
            name='YoutubePlaylist',
            fields=[
            ],
            options={
                'proxy': True,
            },
            bases=('app.playlist',),
        ),
    ]
