import os
import time
import traceback
import json
from copy import deepcopy
from celery import Celery

from multi_vector_simulator.server import run_simulation as mvs_simulation
from multi_vector_simulator.utils.data_parser import convert_epa_params_to_mvs

CELERY_BROKER_URL = (os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379"),)
CELERY_RESULT_BACKEND = os.environ.get(
    "CELERY_RESULT_BACKEND", "redis://localhost:6379"
)

CELERY_TASK_NAME = os.environ.get("CELERY_TASK_NAME", "dev")

app = Celery(CELERY_TASK_NAME, broker=CELERY_BROKER_URL, backend=CELERY_RESULT_BACKEND)


@app.task(name=f"{CELERY_TASK_NAME}.run_simulation")
def run_simulation(simulation_input: dict,) -> dict:
    epa_json = deepcopy(simulation_input)
    dict_values = None
    try:
        dict_values = convert_epa_params_to_mvs(simulation_input)
        simulation_output = mvs_simulation(dict_values)
        simulation_output["SERVER"] = CELERY_TASK_NAME
    except Exception as e:
        simulation_output = dict(
            SERVER=CELERY_TASK_NAME,
            ERROR="{}".format(traceback.format_exc()),
            INPUT_JSON_EPA=simulation_input,
            INPUT_JSON_MVS=dict_values,
        )
    return json.dumps(simulation_output)
