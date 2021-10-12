# syntax=docker/dockerfile:1
FROM ubuntu:latest
FROM python:3.8.10
ARG CONTAINER_HOME
ARG HOST_HOME
ENV HOME=$CONTAINER_HOME
RUN mkdir -p $CONTAINER_HOME/
RUN apt-get update
RUN apt-get -y install git curl vim less
WORKDIR $CONTAINER_HOME

# House keeping
RUN mkdir -p /usr/local/bin
RUN git clone https://github.com/so-fancy/diff-so-fancy.git
RUN ln -s $CONTAINER_HOME/diff-so-fancy/diff-so-fancy /usr/local/bin/diff-so-fancy

# Manually install reqs
COPY . agentos
WORKDIR ./agentos/example_agents/acme_r2d2/
#RUN pip install -r requirements.txt

# Commenting out these, which were copied from
# https://github.com/nickjalbert/acme-test
# where Nick was testing acme in Docker:
#RUN pip install -e .
#RUN pip install --upgrade pip setuptools
#RUN pip install imageio
#RUN pip install dm-acme
#RUN pip install tensorflow
#RUN pip install tensorflow-probability
#RUN pip install dm-acme[reverb]
#RUN pip install dm-acme[envs]
#RUN pip install dm-reverb[tensorflow]
#RUN pip install dm-sonnet
#RUN pip install jax
#RUN pip install jaxlib
#RUN pip install trfl
#RUN pip install imageio
#RUN pip install PILLOW
#RUN pip install pyvirtualdisplay
#RUN pip install launchpad
#RUN pip install flake8
#RUN pip install black