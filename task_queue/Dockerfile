FROM python:3.7-slim

ENV CELERY_BROKER_URL redis://redis:6379/0
ENV CELERY_RESULT_BACKEND redis://redis:6379/0
ENV C_FORCE_ROOT true

RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y git

COPY requirements.txt /tmp/

RUN python -m pip install --upgrade pip
RUN pip install -r /tmp/requirements.txt

COPY . /queue
WORKDIR /queue

ENTRYPOINT celery -A tasks worker --loglevel=info