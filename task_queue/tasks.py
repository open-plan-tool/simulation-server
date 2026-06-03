import os

import time
import traceback
import json
from celery import Celery
from celery.utils.log import get_task_logger
import tempfile
from pathlib import Path

from oemof.datapackage import datapackage  # noqa
from oemof.datapackage import __version__ as dp_version

from oemof.eesyplan import export_results
from oemof.eesyplan.datapackage.energy_system import create_energy_system_from_dp
from oemof.eesyplan.model import optimise


SIMULATION_VERSION = os.environ.get("SIMULATION_VERSION", "no_version")

logger = get_task_logger(__name__)
CELERY_BROKER_URL = (os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379"),)
CELERY_RESULT_BACKEND = os.environ.get(
    "CELERY_RESULT_BACKEND", "redis://localhost:6379"
)

CELERY_TASK_NAME = os.environ.get("CELERY_TASK_NAME", "dev")

app = Celery(CELERY_TASK_NAME, broker=CELERY_BROKER_URL, backend=CELERY_RESULT_BACKEND)


def __run_simulation(simulation_input):
    logger.info("Start new simulation")
    simulation_output = {"SERVER": CELERY_TASK_NAME, "VERSION": SIMULATION_VERSION}
    logger.info(f"Using datapackage version: {dp_version}")
    with tempfile.TemporaryDirectory(prefix="dp_") as td:
        temp_path = Path(td)
        dp_path = datapackage.rebuild_dp_from_json(simulation_input, temp_path)
        try:
            es = create_energy_system_from_dp(dp_path)

            results = optimise(es)

            with tempfile.TemporaryDirectory(prefix="dp_results_") as tres:
                results_path = Path(tres)

                export_results(results, path=results_path)
                json_export = datapackage.export_dp_to_json(results_path)
                simulation_output["raw_results"] = json.loads(json_export)
                # imported_results = import_results(path=results_path, es=es)

        except Exception as e:
            logger.error(
                "An exception occured in the simulation task: {}".format(
                    traceback.format_exc()
                )
            )
            simulation_output.update(
                dict(
                    ERROR="{}".format(traceback.format_exc()),
                    INPUT_JSON=simulation_input,
                )
            )

    return json.dumps(simulation_output)


@app.task(name=f"{CELERY_TASK_NAME}.run_simulation")
def run_simulation(
    simulation_input: dict,
) -> dict:
    return __run_simulation(simulation_input)


@app.task(name=f"{CELERY_TASK_NAME}.get_version")
def get_version() -> str:
    return SIMULATION_VERSION


@app.task(bind=True, name="dev.ping")
def ping(self):
    return {
        "status": "pong",
        "task_id": self.request.id,
        "hostname": socket.gethostname(),
        "pid": os.getpid(),
        "timestamp": time.time(),
    }
