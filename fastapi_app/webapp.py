import os
import json
import io
from fastapi import FastAPI, Request, Response, File, UploadFile
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import StreamingResponse


from multi_vector_simulator import version as mvs_version

from multi_vector_simulator.utils.constants_json_strings import (
    SIMULATION_SETTINGS,
    OUTPUT_LP_FILE,
    VALUE,
    UNIT,
)

MVS_DEV_VERSION = os.environ.get("MVS_DEV_VERSION", mvs_version.version_num)
MVS_OPEN_PLAN_VERSION = os.environ.get("MVS_OPEN_PLAN_VERSION", mvs_version.version_num)

MVS_SERVER_VERSIONS = {"dev": MVS_DEV_VERSION, "open_plan": MVS_OPEN_PLAN_VERSION}

try:
    from worker import app as celery_app
except ModuleNotFoundError:
    from .worker import app as celery_app
import celery.states as states

app = FastAPI()

SERVER_ROOT = os.path.dirname(__file__)

app.mount(
    "/static", StaticFiles(directory=os.path.join(SERVER_ROOT, "static")), name="static"
)

templates = Jinja2Templates(directory=os.path.join(SERVER_ROOT, "templates"))


# option for routing `@app.X` where `X` is one of
# post: to create data.
# get: to read data.
# put: to update data.
# delete: to delete data.

# while it might be tempting to use BackgroundTasks for oemof simulation, those might take up
# resources and it is better to start them in an independent process. BackgroundTasks are for
# not resource intensive processes(https://fastapi.tiangolo.com/tutorial/background-tasks/)


# `127.0.0.1:8000/docs` endpoint will have autogenerated docs for the written code

# Test Driven Development --> https://fastapi.tiangolo.com/tutorial/testing/


@app.get("/")
def index(request: Request) -> Response:

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "mvs_dev_version": MVS_DEV_VERSION,
            "mvs_open_plan_version": MVS_OPEN_PLAN_VERSION,
        },
    )


async def simulate_json_variable(request: Request, queue: str = "dev"):
    """Receive mvs simulation parameter in json post request and send it to simulator"""
    input_dict = await request.json()

    # send the task to celery
    task = celery_app.send_task(
        f"{queue}.run_simulation", args=[input_dict], queue=queue, kwargs={}
    )
    queue_answer = await check_task(task.id)

    return queue_answer


@app.post("/sendjson/")
async def simulate_json_variable_dev(request: Request):
    return await simulate_json_variable(request, queue="dev")


@app.post("/sendjson/openplan")
async def simulate_json_variable_open_plan(request: Request):
    return await simulate_json_variable(request, queue="open_plan")


@app.post("/uploadjson/dev")
def simulate_uploaded_json_files_dev(
    request: Request, json_file: UploadFile = File(...)
):
    """Receive mvs simulation parameter in json post request and send it to simulator
    the value of `name` property of the input html tag should be `json_file` as the second
    argument of this function
    """
    json_content = jsonable_encoder(json_file.file.read())
    return run_simulation(request, input_json=json_content)


@app.post("/uploadjson/open_plan")
def simulate_uploaded_json_files_open_plan(
    request: Request, json_file: UploadFile = File(...)
):
    """Receive mvs simulation parameter in json post request and send it to simulator
    the value of `name` property of the input html tag should be `json_file` as the second
    argument of this function
    """
    json_content = jsonable_encoder(json_file.file.read())
    return run_simulation_open_plan(request, input_json=json_content)


def run_simulation(request: Request, input_json=None, queue="dev") -> Response:
    """Send a simulation task to a celery worker"""

    if input_json is None:
        input_dict = {
            "name": "dummy_json_input",
            "secondary_dict": {"val1": 2, "val2": [5, 6, 7, 8]},
        }
    else:
        input_dict = json.loads(input_json)

    # send the task to celery
    task = celery_app.send_task(
        f"{queue}.run_simulation", args=[input_dict], queue=queue, kwargs={}
    )

    return templates.TemplateResponse(
        "submitted_task.html", {"request": request, "task_id": task.id}
    )


@app.post("/run_simulation")
def run_simulation_dev(request: Request, input_json=None) -> Response:
    return run_simulation(request, input_json, queue="dev")


@app.post("/run_simulation_open_plan")
def run_simulation_open_plan(request: Request, input_json=None) -> Response:
    return run_simulation(request, input_json, queue="open_plan")


@app.get("/check/{task_id}")
async def check_task(task_id: str) -> JSONResponse:
    res = celery_app.AsyncResult(task_id)
    task = {
        "server_info": None,
        "mvs_version": None,
        "id": task_id,
        "status": res.state,
        "results": None,
    }
    if res.state == states.PENDING:
        task["status"] = res.state
    else:
        task["status"] = "DONE"
        results_as_dict = json.loads(res.result)
        server_info = results_as_dict.pop("SERVER")
        task["server_info"] = server_info
        task["mvs_version"] = MVS_SERVER_VERSIONS.get(server_info, "unknown")
        task["results"] = json.dumps(results_as_dict)
        if "ERROR" in task["results"]:
            task["status"] = "ERROR"
            task["results"] = results_as_dict

    return JSONResponse(content=jsonable_encoder(task))


@app.get("/get_lp_file/{task_id}")
async def get_lp_file(task_id: str) -> Response:
    res = celery_app.AsyncResult(task_id)
    task = {
        "server_info": None,
        "mvs_version": mvs_version,
        "id": task_id,
        "status": res.state,
        "results": None,
    }
    if res.state == states.PENDING:
        task["status"] = res.state
        response = JSONResponse(content=jsonable_encoder(task))
    else:
        task["status"] = "DONE"
        results_as_dict = json.loads(res.result)
        server_info = results_as_dict.pop("SERVER")
        task["server_info"] = server_info
        task["mvs_version"] = MVS_SERVER_VERSIONS.get(server_info, "unknown")
        task["results"] = json.dumps(results_as_dict)
        if "ERROR" in task["results"]:
            task["status"] = "ERROR"
            task["results"] = results_as_dict

        if OUTPUT_LP_FILE in results_as_dict[SIMULATION_SETTINGS]:

            stream = io.StringIO(
                results_as_dict[SIMULATION_SETTINGS][OUTPUT_LP_FILE][VALUE]
            )

            response = StreamingResponse(
                iter([stream.getvalue()]), media_type="text/csv"
            )
            response.headers["Content-Disposition"] = "attachment; filename=lp_file.txt"

        else:
            response = "There is no LP file output, did you check the LP file option when you started your simulation?"

    return response
