# Generated by Django 3.2.11 on 2022-02-04 01:01

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("registry", "0008_runcommand"),
    ]

    operations = [
        migrations.AddField(
            model_name="component",
            name="identifier",
            field=models.CharField(default="", max_length=200, unique=True),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="runcommand",
            name="component",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                to="registry.component",
                to_field="identifier",
            ),
        ),
    ]
