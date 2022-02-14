# Generated by Django 3.2.11 on 2022-02-14 18:12

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Component",
            fields=[
                ("created", models.DateTimeField(auto_now_add=True)),
                ("updated", models.DateTimeField(auto_now=True)),
                (
                    "identifier",
                    models.CharField(
                        max_length=200, primary_key=True, serialize=False
                    ),
                ),
                ("name", models.CharField(max_length=200)),
                ("version", models.CharField(max_length=200)),
                ("file_path", models.TextField()),
                ("class_name", models.CharField(max_length=200)),
                ("instantiate", models.BooleanField()),
            ],
        ),
        migrations.CreateModel(
            name="Repo",
            fields=[
                ("created", models.DateTimeField(auto_now_add=True)),
                ("updated", models.DateTimeField(auto_now=True)),
                (
                    "identifier",
                    models.CharField(
                        max_length=200, primary_key=True, serialize=False
                    ),
                ),
                ("type", models.CharField(max_length=200)),
                ("url", models.CharField(max_length=200)),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="RunCommand",
            fields=[
                ("created", models.DateTimeField(auto_now_add=True)),
                ("updated", models.DateTimeField(auto_now=True)),
                (
                    "identifier",
                    models.CharField(
                        max_length=200, primary_key=True, serialize=False
                    ),
                ),
                ("entry_point", models.CharField(max_length=200)),
                ("parameter_set", models.JSONField(default=dict)),
                (
                    "component",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="registry.component",
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="Run",
            fields=[
                ("created", models.DateTimeField(auto_now_add=True)),
                ("updated", models.DateTimeField(auto_now=True)),
                (
                    "identifier",
                    models.CharField(
                        max_length=200, primary_key=True, serialize=False
                    ),
                ),
                ("info", models.JSONField(default=dict)),
                ("data", models.JSONField(default=dict)),
                (
                    "artifact_tarball",
                    models.FileField(
                        null=True, upload_to="artifact_tarballs/"
                    ),
                ),
                (
                    "agent",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="runs_as_agent",
                        to="registry.component",
                    ),
                ),
                (
                    "environment",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="runs_as_environment",
                        to="registry.component",
                    ),
                ),
                (
                    "run_command",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="registry.runcommand",
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="ComponentDependency",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created", models.DateTimeField(auto_now_add=True)),
                ("updated", models.DateTimeField(auto_now=True)),
                ("attribute_name", models.TextField()),
                (
                    "dependee",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="dependee_set",
                        to="registry.component",
                    ),
                ),
                (
                    "depender",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="depender_set",
                        to="registry.component",
                    ),
                ),
            ],
            options={
                "unique_together": {
                    ("depender", "dependee", "attribute_name")
                },
            },
        ),
        migrations.AddField(
            model_name="component",
            name="dependencies",
            field=models.ManyToManyField(
                through="registry.ComponentDependency", to="registry.Component"
            ),
        ),
        migrations.AddField(
            model_name="component",
            name="repo",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="repos",
                to="registry.repo",
            ),
        ),
        migrations.AlterUniqueTogether(
            name="component",
            unique_together={("name", "version")},
        ),
    ]
