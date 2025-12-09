FROM tiangolo/uvicorn-gunicorn-fastapi:python3.11

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
CMD ["gunicorn", "webapp:app", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:5001", "--workers", "4", "--access-logfile","-","--log-level","info"]