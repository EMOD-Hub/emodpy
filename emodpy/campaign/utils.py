from emod_api import campaign as api_campaign
from emod_api import schema_to_class as s2c
import copy


def set_event(broadcast_event: str, event_argument_name: str, campaign: api_campaign, optional: bool = True) -> str:
    """
    Set the event to the campaign module as a broadcast event and return the event name.
    """
    if broadcast_event is None or broadcast_event == '':
        if optional:
            return ''
        else:
            raise ValueError(f"{event_argument_name} must be a string and cannot be None or empty.")
    return campaign.get_send_trigger(broadcast_event, old=True)


def get_trigger_conditions(campaign: api_campaign, trigger_list: list[str]) -> list[str]:
    """
    Get the trigger conditions from the campaign module and return the trigger list.
    """
    def validate_trigger(trigger: str) -> str:
        if not trigger:
            raise ValueError(f"{trigger} must be a string and cannot be None or empty.")
        return trigger
    return [campaign.get_recv_trigger(validate_trigger(trigger), old=True) for trigger in trigger_list]


cached_NSA = None
cached_NSNL = None


def do_nodes(schema_path, node_ids: list[int] = None):
    """
        Create and return a NodeSetConfig based on node_ids list.

    Args:
        schema_path: Path to schema.json file.
        node_ids: a list of NodeIDs, defaults to None, which is NodeSetAll

    Returns:
        Well-configured NodeSetConfig
    """
    if node_ids and len(node_ids) > 0:
        global cached_NSNL
        if cached_NSNL is None:
            cached_NSNL = s2c.get_class_with_defaults("NodeSetNodeList", schema_path)
        nodelist = copy.deepcopy(cached_NSNL)
        nodelist.Node_List = node_ids
    else:
        global cached_NSA
        if cached_NSA is None:
            cached_NSA = s2c.get_class_with_defaults("NodeSetAll", schema_path)
        nodelist = copy.deepcopy(cached_NSA)
    return nodelist
