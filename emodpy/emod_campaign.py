import json
from typing import Dict, List, NoReturn


class EMODCampaign:
    """
    Class representing an EMOD Campaign.
    It contains:
    - events: a list of events for the given campaign
    - name: campaign name
    - use_defaults: EMOD flag to use defaults for unspecified parameters
    - extra_parameters: parameters set by the user that will be added to the campaign JSON
    """

    def __init__(self, name="Campaign", events=None, use_defaults=True, **kwargs):
        self.events = [] if events is None else events
        self.name = name
        self.use_defaults = use_defaults
        self.extra_parameters = kwargs

    @property
    def json(self):
        """
        Property to transform the object in JSON
        """
        return json.dumps({
            "Campaign_Name": self.name,
            "Events": self.events,
            "Use_Defaults": self.use_defaults,
            **self.extra_parameters
        })

    @staticmethod
    def load_from_file(filename: str) -> object:
        """
        Load a campaign from a JSON file.

        Args:
            filename: Path to the campaign file

        Returns: an initialized `EMODCampaign` instance

        """

        with open(filename, 'r') as fp:
            data = json.load(fp)
            return EMODCampaign.load_from_dict(data)

    @staticmethod
    def load_from_dict(data: Dict) -> object:
        """
        Create a campaign object from a dict.
        Args:
            data: The dictionary containing the data

        Returns: an initialized `EMODCampaign` instance

        """
        name = data.pop("Campaign_Name", "Unnamed Campaign")
        events = data.pop("Events", [])
        use_defaults = data.pop("Use_Defaults", 1)
        extra_parameters = data
        return EMODCampaign(name=name, events=events, use_defaults=use_defaults, **extra_parameters)

    def clear(self) -> NoReturn:
        """
        Clear all campaign events
        """
        self.events.clear()

    def get_events_at(self, timestep: int) -> List[Dict]:
        """
        Get a list of events happening at the specified timestep.
        Does not take into account recurrence and only consider start timestep.
        Args:
            timestep: selected timestep

        Returns: list of events

        """
        return list(filter(lambda e: e.get("Start_Day", None) == timestep, self.events))

    def get_events_with_name(self, name: str) -> List[Dict]:
        """
        Get a list of events with the given name.
        This search is based on the `Event_Name` key of events.
        Args:
            name: Name of the events

        Returns: list of events

        """
        return list(filter(lambda e: e.get("Event_Name", None) == name, self.events))

    def add_event(self, event: Dict) -> NoReturn:
        """
        Add the given event to the campaign event.
        Args:
            event: The event to add
        """
        self.events.append(event)

    def add_events(self, events: List[Dict]) -> NoReturn:
        """
        Add a list of events to the campaign events.
        Args:
            events: List of events to add
        """
        self.events.extend(events)

    def __repr__(self):
        out = f"Campaign {self.name}\n"
        out += "Events:\n"
        for event in self.events:
            out += f"  - {event.get('Event_Name', 'Unnamed event')}\n"
            out += f"    Timestep {event.get('Start_Day', 'N/A')} / {event['Event_Coordinator_Config']['Intervention_Config']['class']}\n"

        return out
