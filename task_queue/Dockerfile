FROM python:3.7-slim

ARG mvs_version

ENV CELERY_BROKER_URL redis://redis:6379/0
ENV CELERY_RESULT_BACKEND redis://redis:6379/0
ENV C_FORCE_ROOT true

RUN apt-get update && \
    apt-get install -y git && \
    apt-get install coinor-cbc -y && \
    apt-get install graphviz -y


COPY requirements.txt /tmp/

RUN python -m pip install --upgrade pip
RUN pip install -r /tmp/requirements.txt
# override the multi-vector-simulator latest version
RUN pip install multi-vector-simulator==$mvs_version

COPY . /queue
WORKDIR /queue

ENTRYPOINT celery -A tasks worker --loglevel=info