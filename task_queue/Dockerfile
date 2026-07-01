FROM python:3.12-slim

RUN apt-get update && \
    apt-get install -y git && \
    apt-get install coinor-cbc -y && \
    apt-get install graphviz -y && \
    apt-get install tk -y

COPY task_queue/requirements.txt /tmp/

RUN python -m pip install --upgrade pip
RUN pip install -r /tmp/requirements.txt
# install oemof-eesyplan version from the ENV variable
#RUN pip install "oemof-eesyplan==$SIMULATION_VERSION" gunicorn
RUN pip install "git+https://github.com/oemof/oemof-eesyplan.git@main" --no-cache-dir
RUN pip install gunicorn
RUN pip install "oemof-datapackage @ git+https://github.com/oemof/oemof-datapackage.git"


run echo $(pip freeze)
COPY task_queue/ /queue

# avoid running as root user
RUN useradd --create-home appuser
RUN chown -R appuser /queue
USER appuser

WORKDIR /queue

ENTRYPOINT celery -A tasks worker --loglevel=info --queues=$CELERY_TASK_NAME