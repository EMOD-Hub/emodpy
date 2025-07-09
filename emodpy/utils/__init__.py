from typing import Union, Callable


def is_valid_key_value_pair(s: str) -> bool:
    # Allow empty string as a valid key-value pair
    if s == "":
        return True
    parts = s.split(':')
    # Ensure there are exactly 2 parts (key and value) and neither part is an empty string
    if len(parts) == 2 and parts[0] and parts[1] and parts[0].strip() and parts[1].strip():
        return True
    return False


def validate_key_value_pair(s: str) -> str:
    if not isinstance(s, str):
        raise TypeError(f"Input must be a string, got {type(s).__name__}.")
    # Remove leading and trailing whitespaces in the key:value pair
    s = ":".join([word.strip() for word in s.split(":")])
    # Check if the key-value pair is valid
    if not is_valid_key_value_pair(s):
        raise ValueError(f"Invalid key-value pair: {s}")
    return s


def validate_value_range(param: Union[float, int],
                         param_name: str,
                         min_value: Union[float, None] = None,
                         max_value: Union[float, None] = None,
                         param_type: Union[type] = float):
    """
    Validate that the parameter is within the specified range and of the specified type(float or int only).
    Return the parameter value if it passes the validation.
    """
    if param_type not in [int, float]:
        raise TypeError(f'param_type must be either int or float, got {param_type.__name__}.')

    if param_type == float and not isinstance(param, (float, int)):
        raise ValueError(f'{param_name} must be a float or int, got type = {type(param).__name__}.')

    if param_type == int and not isinstance(param, int):
        raise ValueError(f'{param_name} must be an integer, got type = {type(param).__name__}.')

    if min_value is not None and param < min_value:
        raise ValueError(f'{param_name} must be a {param_type.__name__} greater than or equal to {min_value}, '
                         f'got value = {param}.')

    if max_value is not None and param > max_value:
        raise ValueError(f'{param_name} must be a {param_type.__name__} less than or equal to {max_value}, '
                         f'got value = {param}.')

    return param


def validate_bins(bins: list[float],
                  param_name: str,
                  min_value: Union[float, None] = None,
                  max_value: Union[float, None] = None):
    """
    Validate that the array's values are within the specified range and of the specified type(float or int only) and in
    ascending order.

    Return the parameter value if it passes the validation.
    """
    for i, a_bin in enumerate(bins):
        if type(a_bin) not in [int, float]:
            raise TypeError(f'Each bin must be either int or float, got {type(a_bin).__name__} for {param_name} index {i}.')

    if sorted(bins) != bins:
        raise ValueError(f"{param_name}'s bins must be in ascending order.")

    if min_value is not None and bins[0] < min_value:
        raise ValueError(f"{param_name}'s bins must be a {type(bins[0]).__name__} greater than or equal to {min_value}, "
                         f"got value = {bins[0]}.")

    if max_value is not None and bins[-1] > max_value:
        raise ValueError(f"{param_name}'s bins must be a {type(bins[-1]).__name__} less than or equal to {max_value}, "
                         f"got value = {bins[-1]}.")

    return bins


def validate_node_ids(node_ids: Union[list[int], None]) -> list[int]:
    """todo: validate node_ids against nodes in the demographics file"""
    if node_ids:
        if not isinstance(node_ids, list):
            raise ValueError(f'node_ids must be a list of node_ids, which are integers, not {type(node_ids).__name__}.')
        else:
            for node_id in node_ids:
                if not isinstance(node_id, int):
                    raise ValueError(f'node_ids must be a list integers > 1 and {node_id} is not, '
                                     f'but is {type(node_id).__name__}.')
                else:
                    if node_id < 1:
                        raise ValueError(
                            f'node_ids must be a list of positive integers, but it contains {node_id}.')

            return node_ids
    else:
        return []


def validate_node_property(node_property: str) -> str:
    """Checks if a node property is valid."""
    return node_property


def validate_individual_property(individual_property: str) -> str:
    """Checks if an individual property is valid."""
    return individual_property


def validate_intervention_name(intervention_name: str) -> str:
    """Checks if an individual intervention name is valid."""
    return intervention_name


def validate_individual_event(event: str) -> str:
    """Checks if an individual event is valid."""
    return event


def validate_node_event(event: str) -> str:
    """Checks if an node event is valid."""
    return event


def validate_coordinator_event(event: str) -> str:
    """Checks if an coordinator event is valid."""
    return event


def validate_surveillance_event(event: str):
    """Checks if an coordinator event is valid."""
    return event


def validate_list_of_strings(strings: list[str],
                             param_name: str,
                             process_string_callback: Callable = None,
                             empty_list_ok: bool = False) -> list[str]:
    """
    Helper function to validate a list of strings, ensuring they meet specified conditions.

    Future Work:
    - Ensure the events we are listening for actually exist in the campaign.

    Parameters:
        strings (list[str]): The list of strings to validate.
        param_name (str): The name of the parameter being validated.
        process_string_callback (Callable[[str, bool], None]): Function to process each string.
        empty_list_ok (bool): Whether an empty list is allowed.

    Returns:
        list[str]: The validated list of strings.

    Raises:
        ValueError: If the list is empty and `empty_list_ok` is False.
        ValueError: If `strings` is not a list.
        ValueError: If any string in `strings` does not meet validation criteria.
    """
    if not empty_list_ok and not strings:
        raise ValueError(f'{param_name} must be a list of strings.')
    if empty_list_ok and not strings:
        return []
    if not isinstance(strings, list):
        raise ValueError(f'{param_name} must be a list of strings, got type {type(strings).__name__}.')
    for string in strings:
        if not string:
            raise ValueError(f'{param_name} must be a list of non-empty strings.')
        if not isinstance(string, str):
            raise ValueError(f'{param_name} must be a list of strings, element {string} is type'
                             f' {type(string).__name__}.')
        if process_string_callback:
            process_string_callback(string)
    return strings
