import sys
from pathlib import Path
import unittest
import pytest
from emod_api import campaign as api_campaign
from emodpy.campaign.event import CampaignEventByYear
from emodpy.campaign.event_coordinator import StandardEventCoordinator
from emodpy.campaign.individual_intervention import BroadcastEvent

parent = Path(__file__).resolve().parent
sys.path.append(str(parent))

from base_test import TestHIV, TestMalaria, BaseTestClass


class BaseEventTest(BaseTestClass):
    def test_campaign_event_by_year(self):
        coordinator = StandardEventCoordinator(self.campaign, intervention_list=[BroadcastEvent(self.campaign, "Event1")])
        event = CampaignEventByYear(coordinator, start_year=self.start_year)
        self.assertEqual(event.is_year_supported(self.campaign), self.is_year_supported)


@pytest.mark.unit
class TestScheduledDistributorMalaria(BaseEventTest, TestMalaria):
    def setUp(self):
        TestMalaria().setUp()
        self.campaign = api_campaign
        self.campaign.set_schema(self.schema_path)
        self.start_year = 1990
        self.is_year_supported = False


@pytest.mark.unit
class TestScheduledDistributorHIV(BaseEventTest, TestHIV):
    def setUp(self):
        TestHIV().setUp()
        self.campaign = api_campaign
        self.campaign.set_schema(self.schema_path)
        self.start_year = 1990
        self.is_year_supported = True


if __name__ == '__main__':
    unittest.main()
