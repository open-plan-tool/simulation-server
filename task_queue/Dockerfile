FROM python:3.12-slim

ARG CACHE_BUSTER=1

RUN apt-get update && \
    apt-get install -y git && \
    apt-get install coinor-cbc -y && \
    apt-get install graphviz -y

COPY task_queue/requirements.txt /tmp/

RUN python -m pip install --upgrade pip
RUN pip install -r /tmp/requirements.txt
RUN pip install "git+https://github.com/oemof/oemof-eesyplan.git@op0.0.1" --no-cache-dir
RUN pip install gunicorn
RUN pip install "git+https://github.com/oemof/oemof-datapackage.git@dev"
RUN pip install "git+https://github.com/oemof/oemof-solph@v0.6.4"


run echo $(pip freeze)
COPY task_queue/ /queue

# avoid running as root user
RUN useradd --create-home appuser
RUN chown -R appuser /queue
USER appuser

WORKDIR /queue

ENTRYPOINT celery -A tasks worker --loglevel=info --queues=$CELERY_TASK_NAME