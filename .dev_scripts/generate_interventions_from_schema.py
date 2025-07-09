import argparse
import json
from typing import Dict, List
import copy

# the 5 common parameters that are not disease specific will be handled in the BaseIntervention class in emodpy
# these parameters are common to all interventions: Intervention_Name, Dont_Allow_Duplicates, New_Property_Value,
# Disqualifying_Properties, Cost_To_Consumer
COMMON_PARAMETERS = [
    "Intervention_Name",
    "Dont_Allow_Duplicates",
    "New_Property_Value",
    "Disqualifying_Properties",
    "Cost_To_Consumer"
]
COMMON = [
    "class",
    "iv_type",
    "Sim_Types",
    "idmType:WaningEffect",
    "idmType:RangeThreshold",
    "idmType:IndividualIntervention",
    "idmType:InterpolatedValueMap",
    "idmType:AgeAndProbability",
    "idmType:InsecticideWaningEffect",
    "idmType:WaningConfigList",
    "idmType:Sigmoid"
]
COMMON.extend(COMMON_PARAMETERS)

IDM_TYPES = [
    "idmType:WaningEffect",
    "idmType:RangeThreshold",
    "idmType:IndividualIntervention",
    "idmType:InterpolatedValueMap",
    "idmType:AgeAndProbability",
    "idmType:InsecticideWaningEffect",
    "idmType:WaningConfigList",
    "idmType:Sigmoid",
    "idmAbstractType:IndividualIntervention"
]

IDM_TYPES_NAMES = [i.split(':')[-1] for i in IDM_TYPES]

# for vector types
type_map_funcs = {
    "Vector ": lambda pt: get_vector_type(pt, 1),
    "Vector2d ": lambda pt: get_vector_type(pt, 2),
    "Vector3d ": lambda pt: get_vector_type(pt, 3)}

# for non-vector types, we may add more types as needed,
# e.g. "WaningEffect": "WaningConfig" if we decide to name it a bit differently than the schema
type_map = {
    "Constrained String": "str",
    "string": "str",
    "String": "str",
    "Dynamic String Set": "set(str)",
    "enum": "Enum",
    "integer": "int",
    "IndividualIntervention": "BaseIntervention",
    "InterpolatedValueMap": "ValueMap",
    "Float": "float",
}

# Common interventions that are not disease specific, should be in emodpy
Common_INTERVENTIONS = ["BroadcastEvent",
                        "BroadcastEventToOtherNodes",
                        "ControlledVaccine",
                        "DelayedIntervention",
                        "IndividualImmunityChanger",
                        "IndividualNonDiseaseDeathRateModifier",
                        "MigrateIndividuals",
                        "MultiEffectBoosterVaccine",
                        "MultiEffectVaccine",
                        "MultiInterventionDistributor",
                        "OutbreakIndividual",
                        "PropertyValueChanger",
                        "SimpleBoosterVaccine",
                        "SimpleDiagnostic",
                        "SimpleHealthSeekingBehavior",
                        "SimpleVaccine",
                        "StandardDiagnostic"]

Common_Node_INTERVENTIONS = ["BirthTriggeredIV",
                             "BroadcastCoordinatorEventFromNode",
                             "BroadcastNodeEvent",
                             "ImportPressure",
                             "MigrateFamily",
                             "MultiNodeInterventionDistributor",
                             "NLHTIVNode",  # skip for now
                             "NodeLevelHealthTriggeredIV",  # private
                             "NodePropertyValueChanger",
                             "Outbreak"]


def get_interventions_dict(filename: str) -> Dict:
    with open(filename) as ref_file:
        schema_dict = json.loads(ref_file.read())
    return schema_dict["idmTypes"]["idmAbstractType:Intervention"]


def get_optional_required(param_type: str) -> str:
    return "required" if param_type in IDM_TYPES else "optional"


def get_description(description: str) -> List[str]:
    lines = []
    line_max = 100
    while len(description) > line_max:
        done = False
        index = 0
        prev_index = 0
        while not done:
            index = description[prev_index:].find("\n")
            if (index != -1) and (prev_index + index) < line_max:
                prev_index += index + 1
                done = True
            else:
                index = description[prev_index:].find(" ")
                if index == -1:
                    done = True
                elif index + prev_index < line_max:
                    prev_index += index + 1
                else:
                    done = True
        line = description[:prev_index]
        line = line.replace("\n", "").rstrip()
        lines.append(line)
        description = description[prev_index:]
        # print(len(description))

    if description.find("\n") != -1:
        short_lines = description.split("\n")
        lines.extend(short_lines)
    else:
        lines.append(description)
    return lines


def get_vector_type(param_type: str, dimension: int) -> str:
    base_type = param_type.replace(f"Vector{dimension}d ", "")
    base_type = type_map.get(base_type, base_type)
    if base_type in IDM_TYPES_NAMES:
        return f"{'list[' * dimension}" + f"'{base_type}'" + f"{']' * dimension}"
    else:
        return f"{'list[' * dimension}" + f"{base_type}" + f"{']' * dimension}"


def get_param_type(param_type: str) -> str:
    param_type = param_type.replace("idmType:", "")
    param_type = param_type.replace("idmAbstractType:", "")
    for prefix, func in type_map_funcs.items():
        if param_type.startswith(prefix):
            return func(param_type.replace(prefix, ""))
    return type_map.get(param_type, param_type)


def write_param_definition_in_docs(param: str, schema: Dict) -> str:
    param_type = get_param_type(schema["type"])
    req_opt = get_optional_required(schema["type"])
    desc_lines = get_description(schema["description"])
    text = "\n"
    # rename the type for enums to be actual enum class name
    if param_type == "Enum":
        enum_class_name = param.replace("_", "")
        text += f"        {param.lower()}('{enum_class_name}', {req_opt}):\n"
    else:
        text += f"        {param.lower()}({param_type}, {req_opt}):\n"
    for desc in desc_lines:
        text += "            " + desc + "\n"
    # add min and max values for float and int types
    if param_type == "float" or param_type == "int":
        min_value = schema.get("min")
        max_value = schema.get("max")
        if min_value is not None:
            text += f"            Minimum value: {min_value}\n"
        if max_value is not None:
            text += f"            Maximum value: {max_value}\n"
    # add default value for all types except required
    default_value = schema.get("default", 'required')
    if default_value != 'required':
        # convert 0 and 1 to False and True for bool type
        if param_type == "bool":
            default_value = False if default_value == "0" else True
        default_value = None if default_value in [[], "", "UNINITIALIZED", "UNINITIALIZED STRING"] else default_value
        text += f"            Default value: {default_value}\n"
    return text


def reduce_params(schema: Dict) -> tuple[list[str], list[str]]:
    param_list = []
    distribution_params = []
    common_param_skipped_list = copy.deepcopy(COMMON_PARAMETERS)
    for param in schema.keys():
        if param.endswith("_Distribution") and (schema[param]["default"] == "NOT_INITIALIZED"):
            distribution_params.append(param)
            schema[param]["default"] = "None"

    for param in schema.keys():
        # special handling for intervention_list, schema does not have a correct type for it
        if param.lower() == "intervention_list":
            schema[param]["type"] = "list[BaseIntervention]"
        if param in COMMON:
            if param in COMMON_PARAMETERS:
                common_param_skipped_list.remove(param)
            continue
        elif param in distribution_params:
            param_list.append(param)
        else:
            is_distribution_param = False
            for dist in distribution_params:
                dist = dist.replace("_Distribution", "")
                if param.startswith(dist):
                    is_distribution_param = True
            if not is_distribution_param:
                param_list.append(param)

    # sort the parameters to have the required parameters first
    param_list.sort(key=lambda x: (schema[x].get('default', 'required') == 'required', x), reverse=True)

    return param_list, common_param_skipped_list


def create_code(name: str, schema: Dict, enum_filepath) -> str:
    text = f"class {name}(BaseIntervention):\n"
    text += "    \"\"\"\n"
    text += f"    Create a new {name} intervention.\n"
    text += "\n"
    text += "    Args:\n"
    text += "        campaign (api_campaign, required):\n            An instance of the emod_api.campaign module.\n"
    param_list, common_param_skipped_list = reduce_params(schema)

    for param in param_list:
        def_text = write_param_definition_in_docs(param, schema[param])
        text += def_text
    text += "\n"

    current_common_params = list(set(COMMON_PARAMETERS) - set(common_param_skipped_list))
    if len(current_common_params) > 0:
        text += (f"        common_intervention_parameters (CommomInterventionParameters, optional):\n"
                 f"            The CommonInterventionParameters object that contains the {len(current_common_params)} common\n"
                 f"            parameters: ")
        for i in range(len(current_common_params)):
            current_common_param = current_common_params[i].lower() if current_common_params[i] != 'Cost_To_Consumer' else 'cost'
            if i < len(current_common_params) - 1:
                text += f"{current_common_param}, "
            else:
                text += f"{current_common_param}.\n"

        if len(common_param_skipped_list) > 0:
            text += "            The following parameters are not valid for this intervention:\n"
            for skipped_param in common_param_skipped_list:
                if skipped_param == 'Cost_To_Consumer':
                    text += "            cost\n"
                else:
                    text += f"            {skipped_param.lower()}\n"

        text += "            Default value: None\n"

    text += "    \"\"\"\n"
    text += "\n"
    text += "    def __init__(self,\n"
    text += "                 campaign: api_campaign"

    def format_argument_default_and_typehint(schema: Dict, param: str, param_type: str) -> str:
        default_value = schema[param].get('default', 'required')
        if default_value in [None, [], "", "UNINITIALIZED", "UNINITIALIZED STRING"]:
            default_value = "None"
        else:
            default_value = str(default_value)
        # handle enum types
        if param_type == "Enum":
            enum_class_name = param.replace("_", "")
            param_type = f"'{enum_class_name}'"
            if default_value != "None":
                default_value = f"{enum_class_name}.{default_value}"
        # handle IDM types as class that will be implemented later
        elif param_type in IDM_TYPES_NAMES:
            param_type = f"'{param_type}'"
        # handle bool type
        elif param_type == "bool":
            if default_value == "0":
                default_value = "False"
            elif default_value == "1":
                default_value = "True"
        if default_value == "required":
            return f"                 {param.lower()}: {param_type}"
        else:
            return f"                 {param.lower()}: {param_type} = {default_value}"

    # add arguments with default values and hint types to __init__ method
    for param in param_list:
        param_type = get_param_type(schema[param]["type"])
        text += ",\n"
        text += format_argument_default_and_typehint(schema, param, param_type)
        # add Emod specific enum classes to emod_enum.py
        if param_type == "Enum":
            enum_class_name = param.replace("_", "")
            with open(enum_filepath, "r") as read_file:
                # combine all distribution types into one class
                if 'distribution' in enum_class_name.lower():
                    enum_class_name = "DistributionType"
                if enum_class_name not in read_file.read():
                    with open(enum_filepath, "a") as write_file:
                        write_file.write(f"class {enum_class_name}(StrEnum):\n")
                        for enum in schema[param]["enum"]:
                            write_file.write(f"    {enum} = '{enum}'\n")
                        write_file.write("\n\n")
    if len(common_param_skipped_list) < 5:
        text += ",\n                 common_intervention_parameters: CommomInterventionParameters = None):\n"

        text += f"        super().__init__(campaign, '{name}', common_intervention_parameters)\n\n"
    else:
        text += "                 ):\n"

        text += f"        super().__init__(campaign, '{name}')\n\n"

    text = assign_params_to_intervention(param_list, schema, text)
    text += "\n"
    for param in common_param_skipped_list:
        if param == 'Cost_To_Consumer':
            text += "    def _set_cost(self, cost: float) -> None:\n"
            text += f"        raise ValueError('Cost_To_Consumer is not a valid parameter for the {name} intervention.')\n"
        elif param == 'Disqualifying_Properties':
            text += "    def _set_disqualifying_properties(self, disqualifying_properties: Union[dict[str, str], list[str]]) -> None:\n"
            text += f"        raise ValueError('Disqualifying_Properties is not a valid parameter for the {name} intervention.')\n"
        elif param == "Intervention_Name":
            text += "    def _set_intervention_name(self, intervention_name: str) -> None:\n"
            text += f"        raise ValueError('Intervention_Name is not a valid parameter for the {name} intervention.')\n"
        elif param == "New_Property_Value":
            text += "    def _set_new_property_value(self, new_property_value: str) -> None:\n"
            text += f"        raise ValueError('New_Property_Value is not a valid parameter for the {name} intervention.')\n"
        elif param == "Dont_Allow_Duplicates":
            text += "    def _set_dont_allow_duplicates(self, dont_allow_duplicates: bool) -> None:\n"
            text += f"        raise ValueError('Dont_Allow_Duplicates is not a valid parameter for the {name} intervention.')\n"
        text += "\n"
    text += "\n"

    return text


def assign_params_to_intervention(param_list, schema, text):
    for param in param_list:
        # validate the value range of the parameter for float and int types
        param_type = get_param_type(schema[param]["type"])
        if param_type == "float" or param_type == "int":
            min_value = schema[param].get("min")
            max_value = schema[param].get("max")
            text += f"        self.intervention.{param} = _validate_value_range({param.lower()}, '{param.lower()}', {min_value}, {max_value}, {param_type})\n"
        # handle list of interventions and single intervention
        elif param_type == "list[BaseIntervention]":
            text += f"        self.intervention.{param} = [i.intervention for i in {param.lower()}]\n"
        elif param_type == "BaseIntervention":
            text += f"        self.intervention.{param} = {param.lower()}.intervention\n"
        # handle ValueMap type
        elif param_type == "ValueMap":
            text += f"        self.intervention.{param} = {param.lower()}.map\n"
        # handle broadcasting events
        elif param.lower() != 'event_or_config' and 'event' in param.lower():
            default_value = schema[param].get('default', 'required')
            optional = False if default_value == 'required' else True
            text += "        self.intervention." + param + f" = _set_event({param.lower()}, '{param.lower()}', campaign, {optional})" + "\n"
        # todo: need to add more specific handling for other types, like distribution, etc.
        else:
            text += "        self.intervention." + param + " = " + param.lower() + "\n"
    return text


def ensure_single_blank_line_at_end(file_path):
    # Read the file content
    with open(file_path, 'r') as file:
        lines = file.readlines()

    # Remove trailing blank lines
    while lines and lines[-1].strip() == '':
        lines.pop()

    # Write the modified content back to the file, it will add a blank line at the end
    with open(file_path, 'w') as file:
        file.writelines(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--schema", type=str, default="schema.json",
                        help='Raw schema from a disease specific build of EMOD')
    parser.add_argument("-o", "--output", type=str, default='../emodpy/campaign/HIV_node_interventions.py',
                        help='The file to put the generated code into.')
    parser.add_argument("-c", "--common", type=str, default='../emodpy/campaign/common_node_interventions.py',
                        help='The common intervention file to put the generated code into.')
    parser.add_argument("-a", "--common_append", default=False, action=argparse.BooleanOptionalAction,
                        help='Set to True to write to common intervention file in append mode.')
    parser.add_argument("-e", "--enum", type=str, default='../emodpy/emod_enum.py',
                        help='The enum file to put the generated code into.')
    parser.add_argument("-t", "--type", type=str, default='node', help='individual or node level')

    args = parser.parse_args()

    # write emod_enum.py with StrEnum class, we will add Emod specific enum classes later
    with open(args.enum, "w") as file:
        file.write("from enum import Enum\n\n\n")
        file.write("class StrEnum(str, Enum):\n")
        file.write("    def __str__(self) -> str:\n")
        file.write("        return self.value\n")
        file.write("    pass\n\n\n")

    interventions_dict = get_interventions_dict(args.schema)
    text = ""
    common_text = ""
    disease_specific_interventions = []
    for intervention_type in interventions_dict.keys():
        if ((args.type == "node") and (intervention_type == "idmAbstractType:NodeIntervention")) or (
                (args.type == "individual") and (intervention_type == "idmAbstractType:IndividualIntervention")):
            for intervention_name in interventions_dict[intervention_type]:
                if intervention_name not in Common_INTERVENTIONS and intervention_name not in Common_Node_INTERVENTIONS:
                    disease_specific_interventions.append(intervention_name)
                    text += create_code(intervention_name,
                                        interventions_dict[intervention_type][intervention_name],
                                        args.enum)
                else:
                    common_text += create_code(intervention_name,
                                               interventions_dict[intervention_type][intervention_name],
                                               args.enum)

    # write disease specific interventions to individual_intervention.py and import common interventions from emodpy with __all_exports and __all__
    with open(args.output, 'w') as file:
        for intervention_type in Common_INTERVENTIONS:
            file.write(f"from emodpy.campaign.interventions import {intervention_type} as {intervention_type}\n")
        file.write("from emodpy.campaign.interventions import BaseIntervention, _set_event, _validate_value_range\n")
        file.write("from emodpy.campaign.common import ValueMap\n")
        file.write("from emodpy.emod_enum import *\n")  # todo: update this line later, should not use 'import *'
        file.write("from emod_api import campaign as api_campaign\n\n\n")
        file.write(text)
        file.write("# __all_exports: A list of classes that are intended to be exported from this module.\n")
        file.write("__all_exports = [\n")
        for intervention in disease_specific_interventions:
            file.write(f"    {intervention},\n")
        for intervention in Common_INTERVENTIONS:
            file.write(f"    {intervention},\n")
        file.write("]\n\n")
        file.write("# The following loop sets the __module__ attribute of each class in __all_exports to the name of "
                   "the current module.\n"
                   "# This is done to ensure that when these classes are imported from this module, their __module__ "
                   "attribute correctly\n"
                   "# reflects their source module.\n\n")
        file.write("for _ in __all_exports:\n")
        file.write("    _.__module__ = __name__\n\n")
        file.write("# __all__: A list that defines the public interface of this module.\n")
        file.write("# This is essential to ensure that Sphinx builds documentation for these classes, including those "
                   "that are imported\n"
                   "# from emodpy.\n"
                   "# It contains the names of all the classes that should be accessible when this module is imported "
                   "using the syntax\n"
                   "# 'from module import *'.\n"
                   "# Here, it is set to the names of all classes in __all_exports.\n\n")
        file.write("__all__ = [_.__name__ for _ in __all_exports]\n")

    # keep only the first n lines of the common file
    def keep_only_n_lines(filename, text, n):
        with open(filename, 'r') as file:
            lines = file.readlines()

        with open(filename, 'w') as file:
            for i in range(min(n, len(lines))):
                file.write(lines[i])

    # write common interventions to common_interventions.py
    if args.common_append:
        mode = 'a'
        n = 183
        keep_only_n_lines(args.common, common_text, n)
    else:
        mode = 'w'

    with open(args.common, mode) as file:
        file.write(common_text)
    print("Done")

    for file_path in [args.output, args.common, args.enum]:
        ensure_single_blank_line_at_end(file_path)


if __name__ == "__main__":
    main()
