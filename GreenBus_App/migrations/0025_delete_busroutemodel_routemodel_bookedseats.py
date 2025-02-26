# Generated by Django 5.1.6 on 2025-02-26 11:17

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('GreenBus_App', '0024_remove_routemodel_bookedseats'),
    ]

    operations = [
        migrations.DeleteModel(
            name='BusRouteModel',
        ),
        migrations.AddField(
            model_name='routemodel',
            name='bookedSeats',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.PositiveIntegerField(), blank=True, default=list, size=None),
        ),
    ]
