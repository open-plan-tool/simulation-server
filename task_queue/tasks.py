import os
import time
import logging
import traceback
import json
from copy import deepcopy
from celery import Celery

from multi_vector_simulator.server import (
    run_simulation as mvs_simulation,
    run_sensitivity_analysis_step as mvs_sensitivity_analysis_step,
)
from multi_vector_simulator.utils import set_nested_value, nested_dict_crawler
from multi_vector_simulator.utils.data_parser import convert_epa_params_to_mvs

from sensitivity_analysis_utils import SensitivityAnalysis

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


@app.task(name=f"{CELERY_TASK_NAME}.run_sensitivity_analysis")
def run_sensitivity_analysis(simulation_input: dict,):
    epa_json = deepcopy(simulation_input)

    # parse the sensitivity analysis settings from input json
    sa_settings = SensitivityAnalysis(epa_json)

    if sa_settings.is_valid() is False:
        answer = dict(
            SERVER=CELERY_TASK_NAME,
            ERROR="{}".format(sa_settings.validation_error),
            INPUT_JSON_EPA=epa_json,
            SENSITIVITY_ANALYSIS_SETTINGS=str(sa_settings),
        )
    else:
        mvs_dict = None
        param_val = None

        # start a mvs simulation for the reference scenario
        reference_simulation = run_simulation.apply_async(
            args=[epa_json], queue=CELERY_TASK_NAME
        )
        answer = dict(ref_sim_id=reference_simulation.id, sensitivity_analysis_ids=[])

        try:
            mvs_dict = convert_epa_params_to_mvs(epa_json)
            task_ids = []
            # perform one mvs sensitivity analysis step per value of the variable parameter
            # this is similar to running a simulation, only part of the output is returned
            for i, param_val in enumerate(sa_settings.variable_parameter_range):

                modified_mvs_dict = set_nested_value(
                    mvs_dict, param_val, sa_settings.variable_parameter_name
                )
                result = run_sensitivity_analysis_step.apply_async(
                    args=[modified_mvs_dict, i, sa_settings.output_parameter_names],
                    queue=CELERY_TASK_NAME,
                )
                task_ids.append(result.id)
            answer["sensitivity_analysis_ids"] = task_ids

        except Exception:
            answer["sensitivity_analysis_ids"] = dict(
                SERVER=CELERY_TASK_NAME,
                ERROR="{}".format(traceback.format_exc()),
                INPUT_PARAM_PATH=sa_settings.variable_parameter_name,
                INPUT_PARAM_VAL=param_val,
                PARAM_PATHES=nested_dict_crawler(mvs_dict),
            )

    return answer


@app.task(name=f"{CELERY_TASK_NAME}.run_sensitivity_analysis_step")
def run_sensitivity_analysis_step(
    mvs_dict: dict, step_idx: int, output_variables: list
) -> dict:
    mvs_dict
    try:
        simulation_output = mvs_sensitivity_analysis_step(
            mvs_dict, step_idx, output_variables
        )
        simulation_output["SERVER"] = CELERY_TASK_NAME
    except Exception as e:
        simulation_output = dict(
            SERVER=CELERY_TASK_NAME,
            ERROR="{}".format(traceback.format_exc()),
            step_idx=step_idx,
            INPUT_JSON_MVS=mvs_dict,
            OUTPUT_VARIABLES=output_variables,
        )
    return json.dumps(simulation_output)
