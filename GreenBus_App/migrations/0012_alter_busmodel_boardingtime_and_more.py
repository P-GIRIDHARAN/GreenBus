# Generated by Django 5.1.6 on 2025-02-25 09:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('GreenBus_App', '0011_alter_busmodel_boardingtime'),
    ]

    operations = [
        migrations.AlterField(
            model_name='busmodel',
            name='boardingTime',
            field=models.CharField(choices=[('Morning', '9AM'), ('Night', '9PM')]),
        ),
        migrations.AlterField(
            model_name='paymentmodel',
            name='paymentStatus',
            field=models.CharField(choices=[('Paid', 'Successful'), ('Not Paid', 'Not Successful')], default='Not Paid', max_length=10),
        ),
    ]
