# mvs_eland_api
Creates API server to dispatch mvs simulation tasks to a queue of workers.
The API typically recieves a post request with a json input file, sends this file to a parser which
initiate a long simulation (like [oemof](https://github.com/oemof/oemof)). Once the simulation
 is done a json response is sent back. The json results can also be retrieved with the task id.

## Get started

Run `sudo docker-compose up -d --build` to run the task queue and the webapp simulaneously.

Now the webapp is available at `127.0.0.1:5001`

Run `sudo docker-compose down` to shut the services down.

## Develop while services are running

### Using [redis](https://redis.io/documentation)

You have to start redis-server
`service redis-server start`
(to stop it use `service redis-server stop`)
Move to `task_queue` and run `. setup_redis.sh` to start the celery queue with redis a message
 broker.

### Using [RabbitMQ](https://www.rabbitmq.com/getstarted.html)

### Using [fastapi](https://fastapi.tiangolo.com/)

In another terminal go the the root of the repo and run `. fastapi_run.sh`

Now the fastapi app is available at `127.0.0.1:5001`


## Docs

To build the docs simply go to the `docs` folder

    cd docs

Install the requirements

    pip install -r docs_requirements.txt

and run

    make html

The output will then be located in `docs/_build/html` and can be opened with your favorite browser

## Code linting

Use `black .` to lint the python files inside the repo

