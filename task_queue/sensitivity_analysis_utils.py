import jsonschema
import traceback
from multi_vector_simulator.utils.data_parser import MAP_EPA_MVS


SA_SCHEMA = {
    "type": "object",
    "required": [
        "variable_parameter_name",
        "variable_parameter_range",
        "variable_parameter_ref_val",
        "output_parameter_names",
    ],
    "properties": {
        "variable_parameter_name": {
            "oneOf": [{"type": "array", "items": {"type": "string"}}]
        },
        "variable_parameter_range": {"type": "array", "items": {"type": "number"}},
        "variable_parameter_ref_val": {"type": "number"},
        "output_parameter_names": {"type": "array", "items": {"type": "string"}},
    },
    "additionalProperties": False,
}

SENSITIVITY_ANALYSIS_SETTINGS = "sensitivity_analysis_settings"


class SensitivityAnalysis:
    __raw_input = None
    variable_parameter_name = None
    variable_parameter_range = None
    variable_parameter_ref_val = None
    output_parameter_names = None
    validation_error = ""

    def __init__(self, dict_settings):
        sa_settings = dict_settings.get(SENSITIVITY_ANALYSIS_SETTINGS, None)
        self.__raw_input = sa_settings
        if sa_settings is not None:
            try:
                jsonschema.validate(sa_settings, SA_SCHEMA)
                schema_is_valid = True
            except jsonschema.exceptions.ValidationError as e:
                schema_is_valid = False
                self.validation_error = "{}".format(traceback.format_exc())

            if schema_is_valid is True:
                self.variable_parameter_name = sa_settings.get(
                    "variable_parameter_name", None
                )
                self.format_parameter_name()

                self.variable_parameter_range = sa_settings.get(
                    "variable_parameter_range", None
                )
                self.output_parameter_names = sa_settings.get(
                    "output_parameter_names", None
                )
                self.variable_parameter_ref_val = sa_settings.get(
                    "variable_parameter_ref_val", None
                )
        else:
            self.validation_error = (
                f"The key {SENSITIVITY_ANALYSIS_SETTINGS} is missing in the input json"
            )

    def format_parameter_name(self):
        if self.variable_parameter_name is not None:
            self.variable_parameter_name = tuple(
                [MAP_EPA_MVS.get(key, key) for key in self.variable_parameter_name]
            )

    def is_valid(self):
        if (
            self.variable_parameter_name is not None
            and self.variable_parameter_range is not None
            and self.output_parameter_names is not None
            and self.variable_parameter_ref_val
        ):
            answer = True
            if self.variable_parameter_ref_val not in self.variable_parameter_range:
                answer = False
                self.validation_error = (
                    f"The value ({self.variable_parameter_ref_val}) of the variable parameter"
                    f" {'.'.join(self.variable_parameter_name)} for the reference scenario of"
                    " the sensitivity analysis is not within the variable range provided"
                    f": [{', '.join([str(p) for p in self.variable_parameter_range]) }]"
                )
        else:
            answer = False
        return answer

    def __str__(self):
        return str(self.__raw_input)


if __name__ == "__main__":
    import json

    with open("test_sa.json", "r") as jf:
        input_dict = json.load(jf)

    # with open("AFG_epa_format.json", "w") as jf:
    #     json.dump(input_dict, jf, indent=4)

    # input_dict[SENSITIVITY_ANALYSIS_SETTINGS] = {
    #     "variable_parameter_name": ["energy_busses"],
    #     "variable_parameter_range": [1, 2, 3.2, 3.5],
    #     "variable_parameter_ref_val": 3,
    #     "output_parameter_names": [
    #         "specific_emissions_per_electricity_equivalent",
    #         "total_feedinElectricity",
    #         "total_internal_generation",
    #         "peak_flow",
    #     ],
    # }
    sa = SensitivityAnalysis(input_dict)
    print(sa.is_valid(), sa.validation_error)
    import ipdb

    ipdb.set_trace()
    # input_dict[SENSITIVITY_ANALYSIS_SETTINGS] = {
    #     "variable_parameter_name": [
    #         "energy_providers",
    #         "Grid_DSO",
    #         "energy_price",
    #         "value",
    #     ],
    #     "variable_parameter_range": [1, 2, 3, 3.5],
    #     "variable_parameter_ref_val": 3,
    #     "output_parameter_names": [
    #         "specific_emissions_per_electricity_equivalent",
    #         "total_feedinElectricity",
    #         "total_internal_generation",
    #         "peak_flow",
    #     ],
    # # }
    # sa = SensitivityAnalysis(input_dict)
    # print(sa.is_valid(), sa.validation_error)
    # sa = SensitivityAnalysis({SENSITIVITY_ANALYSIS_SETTINGS: {
    #     "variable_parameter_name": "",
    #     "variable_parameter_range": "",
    #     "variable_parameter_ref_val": "",
    #     "output_parameter_names": "",
    # }})
