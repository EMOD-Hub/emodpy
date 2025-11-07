from typing import Optional, List

from emod_api import campaign as api_campaign, schema_to_class as s2c

from emodpy.campaign.event_coordinator import BaseEventCoordinator
from emodpy.utils import validate_value_range


class BaseEvent:
    """
    Base class for CampaignEvent and CampaignEventByYear.
    The "Events" array in the campaign.json file is a list of these objects. They define the "when" and "where" an intervention is to be distributed.

    Args:
        coordinator (BaseEventCoordinator, required):
            - An EventCoordinator object that determines "who", "what", and "why" an intervention is distributed.
            - It specifies which Event Coordinator class will handle the event, and then configures the coordinator.
        event_class_name (str, required):
            - The event class name, i.e. CampaignEvent or CampaignEventByYear
        event_name (str, optional):
            - The name of the event.
            - Defaults to "Campaign_Event".
        node_ids (Optional[List[int]], optional):
            - A list of node IDs where the EventCoordinator will consider distributing the intervention in.
            - If None, then all nodes will be considered
            - Defaults to None.

    Returns:
        None

    """
    def __init__(self,
                 coordinator: BaseEventCoordinator,
                 event_class_name: str,
                 event_name: str,
                 node_ids: Optional[List[int]] = None):
        """
        Initializes a base CampaignEvent object with the given parameters.
        """
        self.coordinator = coordinator
        self.event_class_name = event_class_name
        self.event_name = event_name
        self.node_ids = node_ids if node_ids is not None else []

    def to_schema_dict(self, campaign: api_campaign) -> s2c.ReadOnlyDict:
        """
        Return a CampaignEvent or CampaignEventByYear event with the specified parameters.

        Args:
            campaign (api_campaign, required):
                - The campaign object to which the event will be added. This should be an instance of the emod_api.campaign class.

        Returns:
            s2c.ReadOnlyDict: The CampaignEvent or CampaignEventByYear event.
        """
        self._event = s2c.get_class_with_defaults(self.event_class_name, campaign.schema_path)
        self._event.Event_Coordinator_Config = self.coordinator.to_schema_dict()

        if self.node_ids:
            node_conf = s2c.get_class_with_defaults("NodeSetNodeList", campaign.schema_path)
            node_conf.Node_List = self.node_ids
        else:
            node_conf = s2c.get_class_with_defaults("NodeSetAll", campaign.schema_path)
        self._event.Nodeset_Config = node_conf

        if self.event_name:
            self._event['Event_Name'] = self.event_name  # Event_Name is not in Schema

        return self._event


class CampaignEventByYear(BaseEvent):
    """
    The CampaignEventByYear event class determines when to distribute the intervention based on the calendar year.

    Args:
        coordinator (BaseEventCoordinator, required):
            - An EventCoordinator object that determines "who", "what", and "why" an intervention is distributed.
            - It specifies which Event Coordinator class will handle the event, and then configures the coordinator.
        start_year (float, required):
            - The absolute year of the simulation to activate the event’s event coordinator.
            - To have the intervention applied other than at the beginning of the year, you must enter a decimal value after the year. For example, 2010.5 would have the intervention applied halfway through the year 2010.
            - Maximum value is 2200
            - Minimum value is 1900
        event_name (str, optional):
            - The name of the event.
            - Defaults to None.
        node_ids (Optional[List[int]], optional):
            - A list of node IDs where the EventCoordinator will consider distributing the intervention in.
            - If None, then all nodes will be considered
            - Defaults to None.

    """
    def __init__(self,
                 coordinator: BaseEventCoordinator,
                 start_year: float,
                 event_name: str = None,
                 node_ids: Optional[List[int]] = None):
        """
        Initializes a CampaignEventByYear object with the given parameters.
        """
        super().__init__(coordinator=coordinator, event_class_name="CampaignEventByYear",
                         event_name=event_name, node_ids=node_ids)
        self.start_year = validate_value_range(start_year, "start_year", min_value=1900, max_value=2200, param_type=float)

    def to_schema_dict(self, campaign: api_campaign) -> s2c.ReadOnlyDict:
        """
        Return a CampaignEventByYear event with the specified parameters.

        Args:
            campaign (api_campaign, required):
                - The campaign object to which the event will be added. This should be an instance of the emod_api.campaign class.

        Returns:
            s2c.ReadOnlyDict: The CampaignEvent or CampaignEventByYear event.
        """
        super().to_schema_dict(campaign)
        self._event.Start_Year = self.start_year
        return self._event

    def is_year_supported(self, campaign: api_campaign) -> bool:
        """
        Check if the year is supported by the campaign.

        Args:
            campaign (api_campaign, required):
                - The campaign object to which the event will be added. This should be an instance of the emod_api.campaign class.

        Returns:
            bool: True if the year is supported, otherwise False.
        """
        try:
            event = s2c.get_class_with_defaults(self.event_class_name, campaign.schema_path)
        except ValueError:
            return False

        return hasattr(event, 'Start_Year')


class CampaignEvent(BaseEvent):
    """
    The CampaignEvent event class determines when to distribute the intervention based on the day of the simulation.

    Args:
        coordinator (BaseEventCoordinator, required):
            - An EventCoordinator object that determines "who", "what", and "why" an intervention is distributed.
            - It specifies which Event Coordinator class will handle the event, and then configures the coordinator.
        start_day (float, required):
            - The absolute day of the simulation to activate the event’s event coordinator.
            - Maximum value is 3.40282e+38
            - Minimum value is 0
        event_name (str, optional):
            - The name of the event.
            - Defaults to None.
        node_ids (Optional[List[int]], optional):
            - A list of node IDs where the EventCoordinator will consider distributing the intervention in.
            - If None, then all nodes will be considered
            - Defaults to None.
    """
    def __init__(self,
                 coordinator: BaseEventCoordinator,
                 start_day: float,
                 event_name: str = None,
                 node_ids: Optional[List[int]] = None):
        """
        Initializes a CampaignEvent object with the given parameters.
        """
        super().__init__(coordinator=coordinator, event_class_name="CampaignEvent",
                         event_name=event_name, node_ids=node_ids)
        self.start_day = validate_value_range(start_day, "start_day", min_value=0, max_value=3.40282e+38, param_type=float)

    def to_schema_dict(self, campaign: api_campaign) -> s2c.ReadOnlyDict:
        """
        Return a CampaignEvent event with the specified parameters.

        Args:
            campaign (api_campaign, required):
                - The campaign object to which the event will be added. This should be an instance of the emod_api.campaign class.

        Returns:
            s2c.ReadOnlyDict: The CampaignEvent or CampaignEventByYear event.
        """
        super().to_schema_dict(campaign)
        self._event.Start_Day = self.start_day
        return self._event


def create_campaign_event(campaign: api_campaign,
                          coordinator: BaseEventCoordinator,
                          event_name: str = None,
                          node_ids: Optional[List[int]] = None,
                          start_day: Optional[float] = None,
                          start_year: Optional[float] = None) -> BaseEvent:
    """
    Create a CampaignEvent or CampaignEventByYear event with the specified parameters and return it.
    """
    # Check that not both start_day or start_year are set.
    if start_day is not None and start_year is not None:
        raise ValueError("Either start_day or start_year is required, but not both.")
    # Configure CampaignEventByYear if start_year is defined.
    elif start_year is not None:
        event = CampaignEventByYear(coordinator=coordinator, start_year=start_year, event_name=event_name,
                                    node_ids=node_ids)
        # Check that the start_year is supported in the disease model.
        if not event.is_year_supported(campaign=campaign):
            raise ValueError("The start_year is not supported in this disease model, please use start_day.")
    # Configure CampaignEvent if start_day is defined.
    elif start_day is not None:
        event = CampaignEvent(coordinator=coordinator, start_day=start_day, event_name=event_name,
                              node_ids=node_ids)
    # Check that at least one of start_day or start_year is set.
    else:
        raise ValueError("Either start_day or start_year is required.")

    return event
