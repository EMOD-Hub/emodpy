from dataclasses import dataclass, field

from emodpy.reporters.base import BuiltInReporter
from emod_api import schema_to_class as s2c


@dataclass
class ReportNodeDemographics(BuiltInReporter):
    Stratify_By_Gender: bool = field(default=False)
    Age_Bins: list = field(default_factory=list)
    class_name: str = field(default="ReportNodeDemographics")


@dataclass
class ReportHumanMigrationTracking(BuiltInReporter):
    def config(self, config_builder, manifest):
        self.class_name = "ReportHumanMigrationTracking"  # OK to hardcode? config["class"]
        rhmt_params = s2c.get_class_with_defaults("ReportHumanMigrationTracking", manifest.schema_file)
        rhmt_params = config_builder(rhmt_params)
        rhmt_params.finalize()
        rhmt_params.pop("Sim_Types")  # maybe that should be in finalize
        self.parameters.update(dict(rhmt_params))
