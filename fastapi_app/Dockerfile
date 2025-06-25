FROM tiangolo/uvicorn-gunicorn:python3.10

ENV CELERY_BROKER_URL redis://redis:6379/0
ENV CELERY_RESULT_BACKEND redis://redis:6379/0

COPY fastapi_app/requirements.txt /tmp/

# install requirements
RUN python -m pip install --upgrade pip
RUN pip install -r /tmp/requirements.txt
# install multi-vector-simulator's version pinned in docker-compose.yml file
RUN pip install multi-vector-simulator==1.0.7rc3 gunicorn



COPY fastapi_app/ /fastapi_app

# avoid running as root user
RUN useradd --create-home appuser
RUN chown -R appuser /fastapi_app
USER appuser
WORKDIR /fastapi_app

# expose the app port
EXPOSE 5001

# run the app server, the last argument match the app variable in the webapp.py file
CMD ["uvicorn", "fastapi_app.webapp:app", "--host", "0.0.0.0", "--port", "5001", "--proxy-headers"]
