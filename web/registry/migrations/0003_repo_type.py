# Generated by Django 3.2.11 on 2022-01-31 22:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("registry", "0002_component_instantiate"),
    ]

    operations = [
        migrations.AddField(
            model_name="repo",
            name="type",
            field=models.CharField(default="github", max_length=200),
            preserve_default=False,
        ),
    ]
