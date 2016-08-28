# -*- coding: utf-8 -*-
# Generated by Django 1.10 on 2016-08-28 17:05
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Game',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_time', models.DateTimeField(auto_now_add=True)),
                ('title', models.CharField(max_length=100)),
            ],
            options={
                'verbose_name': 'spil',
                'verbose_name_plural': 'spil',
                'ordering': ['title'],
            },
        ),
        migrations.CreateModel(
            name='Option',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('kind', models.CharField(choices=[('canonical', 'Kanonisk'), ('alias', 'Alias'), ('unconfirmed', 'Ny')], max_length=20, verbose_name='slags')),
                ('text', models.CharField(max_length=200, verbose_name='navn')),
                ('alias_target', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='mastermind.Option')),
                ('game', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='mastermind.Game')),
            ],
            options={
                'verbose_name': 'valgmulighed',
                'verbose_name_plural': 'valgmuligheder',
                'ordering': ['game', 'text'],
            },
        ),
        migrations.CreateModel(
            name='Profile',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(blank=True, max_length=200, verbose_name='Navn')),
                ('created_time', models.DateTimeField(auto_now_add=True)),
                ('user', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Slot',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('position', models.IntegerField()),
                ('stem', models.CharField(max_length=200, verbose_name='navn')),
                ('game', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='mastermind.Game')),
                ('key', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='mastermind.Option')),
            ],
            options={
                'verbose_name': 'indgang',
                'verbose_name_plural': 'indgange',
                'ordering': ['game', 'position'],
            },
        ),
        migrations.CreateModel(
            name='Submission',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('option', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='mastermind.Option')),
                ('profile', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='mastermind.Profile')),
                ('slot', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='mastermind.Slot')),
            ],
            options={
                'verbose_name': 'gæt',
                'verbose_name_plural': 'gæt',
                'ordering': ['slot', 'profile'],
            },
        ),
        migrations.AddField(
            model_name='game',
            name='owner',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='mastermind.Profile'),
        ),
        migrations.AlterUniqueTogether(
            name='submission',
            unique_together=set([('profile', 'slot')]),
        ),
    ]