import os
import time
import json
from celery import Celery

from mvs_eland_tool import run_simulation as mvs_simulation

CELERY_BROKER_URL = (os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379"),)
CELERY_RESULT_BACKEND = os.environ.get(
    "CELERY_RESULT_BACKEND", "redis://localhost:6379"
)

celery = Celery("tasks", broker=CELERY_BROKER_URL, backend=CELERY_RESULT_BACKEND)


@celery.task(name="tasks.run_simulation")
def run_simulation(simulation_input: dict,) -> dict:
    simulation_input = json.loads(simulation_input)
    try:
        simulation_output = mvs_simulation(simulation_input)
    except Exception as e:
        simulation_output = "{}".format(e)

    return json.dumps(simulation_output)
