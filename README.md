# simulation-server

The open-plan-tool/gui sends simulation requests to a simulation server so that you can queue tasks and still use the app while the simulation to be done. The server can be running on your local computer, or you can set it up online. An online server hosted by Reiner Lemoine Institut is setup by default for open-plan-tool/gui


The code in this repository creates the simulation server and a basic server API to dispatch [mvs](https://github.com/rl-institut/multi-vector-simulator) simulation tasks to a queue of workers.
The API typically receives a post request with a json input file, sends this file to a parser which
initiate an MVS simulation. Once the simulation is done, a json response is sent back. The json results can also be retrieved with the task id.

## Get started

Run `sudo docker-compose up -d --build` to run the task queue and the webapp simultaneously.

Now the webapp is available at `127.0.0.1:5001`

Use

    sudo docker-compose logs web

to get the logs messages of the `web` service of the docker-compose.yml file


Run `sudo docker-compose down` to shut the services down.

## Develop while services are running

### Using [redis](https://redis.io/documentation)

#### Ubuntu [install instructions](https://www.digitalocean.com/community/tutorials/how-to-install-and-secure-redis-on-ubuntu-18-04)

    sudo apt update
    sudo apt install redis-server

Then go in redis conf file

    sudo nano /etc/redis/redis.conf

and look for `supervised` parameter, set it to `systemd`

    supervised systemd


Then start the service with

    sudo systemctl restart redis.service

or

    sudo service redis-server start

(to stop it use `sudo service redis-server stop`)
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

