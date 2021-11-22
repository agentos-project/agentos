# Generated by Django 3.2.7 on 2021-11-19 20:24

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("registry", "0002_rename_alias_componentdependency_attribute_name"),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name="component",
            unique_together={("name", "version")},
        ),
        migrations.AlterUniqueTogether(
            name="componentdependency",
            unique_together={("depender", "dependee", "attribute_name")},
        ),
    ]