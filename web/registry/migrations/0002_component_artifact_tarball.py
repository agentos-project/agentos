# Generated by Django 3.2.13 on 2022-06-19 13:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("registry", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="component",
            name="artifact_tarball",
            field=models.FileField(null=True, upload_to="artifact_tarballs/"),
        ),
    ]
