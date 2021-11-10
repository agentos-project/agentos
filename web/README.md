# AgentOS Web

A prototype of the AgentOS web service. Related
[discussion](https://github.com/agentos-project/agentos/discussions/139).

Designed to be run in tandem with the the AgentOS code in the `nj_leaderboard`
branch of this [AgentOS
fork](https://github.com/nickjalbert/agentos/tree/nj_leaderboard)


## Set up a local version

Built with Python 3.9 and Postgres 12.8.

```bash
git clone git@github.com:nickjalbert/aos_web.git
cd aos_web
virtualenv -p /usr/bin/python3.9 env
source env/bin/activate
pip install -r requirements.txt
# Create postgres database aos_web with aos_web_user with pwd aabbccdd:
sudo service postgresql start
sudo -u postgres psql
create database aos_web;
create user aos_web_user with encrypted password 'aabbccdd';
grant all privileges on database aos_web to aos_web_user;
./manage.py migrate
./manage.py runserver
# navigate to http://localhost:8000

```

## Notes

```bash
./manage.py import_registry https://raw.githubusercontent.com/nickjalbert/agentos/nj_leaderboard/registry.yaml
```

## Installation and Setup Info

Raw notes from installation and setup:


```bash
# Create virtual env
virtualenv -p /usr/bin/python3.9 env
source env/bin/activate
# Setup Django
pip install Django
django-admin startproject aos_web
cd aos_web/
./manage.py startapp registry
# Follow tutorial:
# https://docs.djangoproject.com/en/3.2/intro/tutorial01/

# Setup postgres
sudo apt install postgresql postgresql-contrib
sudo passwd postgres # XXXXXXXX
sudo service postgresql start
sudo -u postgres psql
postgres=# create database aos_web;
CREATE DATABASE
postgres=# create user aos_web_user with encrypted password 'XXXXXXXX';
CREATE ROLE
postgres=# grant all privileges on database aos_web to aos_web_user;
# added models and updated settings
./manage.py makemigrations
./manage.py migrate
python manage.py createsuperuser


# Heroku deployment
# https://medium.com/geekculture/how-to-deploy-a-django-app-on-heroku-4d696b458272
pip3 install gunicorn dj-database-url whitenoise psycopg2-binary
# Setup heroku CLI
curl https://cli-assets.heroku.com/install-ubuntu.sh | sh
# Bunch of settings.py updates from the medium article
heroku create aos-web
git push heroku main
heroku addons:create heroku-postgresql:hobby-dev --app aos-web
heroku run python manage.py migrate
heroku run python manage.py createsuperuser
heroku open
# set IS_DEPLOY=True on Heroku config vars dashboard (under settings)
```
