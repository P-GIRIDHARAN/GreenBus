# Generated by Django 5.1.6 on 2025-02-26 11:09

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('GreenBus_App', '0023_busroutemodel_routemodel'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='routemodel',
            name='bookedSeats',
        ),
    ]
