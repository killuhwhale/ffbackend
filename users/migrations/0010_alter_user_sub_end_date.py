# Generated by Django 4.0.6 on 2023-06-14 02:23

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0009_alter_user_sub_end_date'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='sub_end_date',
            field=models.DateTimeField(default=datetime.datetime(2023, 6, 13, 2, 23, 8, 894998), verbose_name='sub_end_date'),
        ),
    ]
