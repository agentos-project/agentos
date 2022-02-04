# Generated by Django 3.2.11 on 2022-02-03 23:56

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('registry', '0007_remove_component_description'),
    ]

    operations = [
        migrations.CreateModel(
            name='RunCommand',
            fields=[
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('identifier', models.CharField(max_length=200, primary_key=True, serialize=False, unique=True)),
                ('entry_point', models.CharField(max_length=200)),
                ('parameter_set', models.JSONField(default=dict)),
                ('component', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='registry.component')),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
