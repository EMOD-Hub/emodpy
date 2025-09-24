from emod_api import campaign as api_campaign


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
