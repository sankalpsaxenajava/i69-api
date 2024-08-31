# pull official base image
FROM python:3.9.12

ARG APP_HOME=/home/i69
RUN apt-get update \
  && apt-get install --no-install-recommends --yes supervisor nginx

# accept arguments
ARG PIP_REQUIREMENTS=requirements.txt

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# install dependencies
RUN pip install --upgrade pip setuptools

# set work directory
WORKDIR ${APP_HOME}

COPY requirements.txt .
RUN pip3 install -r requirements.txt
COPY . .
RUN pip3 install opencv-python-headless==4.5.3.56
COPY ./docker/.conf.d/supervisor/supervisord.conf /etc/supervisor/supervisord.conf
COPY ./docker/.conf.d/nginx/nginx.conf /etc/nginx/nginx.conf
COPY ./docker/.conf.d/nginx/i69.conf /etc/nginx/conf.d/default.conf
# create supervisor socket directory
RUN mkdir -p /home/i69/env/run/supervisor

ENTRYPOINT ["/bin/bash","/home/i69/docker/entrypoint.sh"]
