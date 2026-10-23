FROM python:3.12-slim

ARG CACHE_BUST=2

RUN apt-get update && \
    apt-get install -y git && \
    apt-get install coinor-cbc -y && \
    apt-get install graphviz -y

COPY task_queue/requirements.txt /tmp/

RUN python -m pip install --upgrade pip
RUN pip install -r /tmp/requirements.txt
# install oemof-eesyplan version from the ENV variable
#RUN pip install "oemof-eesyplan==$SIMULATION_VERSION" gunicorn
RUN pip install "git+https://github.com/oemof/oemof-eesyplan.git@op0.0.3" --no-cache-dir
RUN pip install gunicorn
#RUN pip install "oemof-datapackage @ git+https://github.com/oemof/oemof-datapackage.git@op0.0.2"
#RUN pip install "git+https://github.com/oemof/oemof-solph@a4611edb8a225ee6faa360f86afc49d2986c1105"


run echo $(pip freeze)
COPY task_queue/ /queue

# avoid running as root user
RUN useradd --create-home appuser
RUN chown -R appuser /queue
USER appuser

WORKDIR /queue

ENTRYPOINT celery -A tasks worker --loglevel=info --queues=$CELERY_TASK_NAME