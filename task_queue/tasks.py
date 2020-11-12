import os
import time
import traceback
import json
from celery import Celery

from multi_vector_simulator.server import run_simulation as mvs_simulation
from multi_vector_simulator.utils.data_parser import convert_epa_params_to_mvs

CELERY_BROKER_URL = (os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379"),)
CELERY_RESULT_BACKEND = os.environ.get(
    "CELERY_RESULT_BACKEND", "redis://localhost:6379"
)

celery = Celery("tasks", broker=CELERY_BROKER_URL, backend=CELERY_RESULT_BACKEND)


@celery.task(name="tasks.run_simulation")
def run_simulation(
    simulation_input: dict,
) -> dict:

    try:

        dict_values = convert_epa_params_to_mvs(simulation_input)

        simulation_output = mvs_simulation(dict_values)

    except Exception as e:

        simulation_output = "ERROR: {}".format(traceback.format_exc())

    return json.dumps(simulation_output)
