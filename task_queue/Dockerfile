FROM python:3.12-slim

RUN apt-get update && \
    apt-get install -y git && \
    apt-get install coinor-cbc -y && \
    apt-get install graphviz -y

COPY task_queue/requirements.txt /tmp/

RUN python -m pip install --upgrade pip
RUN pip install -r /tmp/requirements.txt
# install oemof-eesyplan version from the ENV variable
#RUN pip install "oemof-eesyplan==$SIMULATION_VERSION" gunicorn
RUN pip install gunicorn
RUN echo "Trigger below"
RUN pip install "git+https://github.com/oemof/oemof-eesyplan.git@fix/openplan_simulation"
RUN pip install "oemof-datapackage @ git+https://github.com/oemof/oemof-datapackage.git@fix/openplan-to-eesyplan-parsing"


run echo $(pip freeze)
COPY task_queue/ /queue

# avoid running as root user
RUN useradd --create-home appuser
RUN chown -R appuser /queue
USER appuser

WORKDIR /queue

ENTRYPOINT celery -A tasks worker --loglevel=info --queues=$CELERY_TASK_NAME