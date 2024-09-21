from dataclasses import dataclass
from typing import NoReturn
from idmtools.entities.command_line import CommandLine

from emodpy.emod_task                 import EMODTask

@dataclass()
class KF_EMODTask(EMODTask):

    def set_command_line(self) -> NoReturn:
        """
        Builds and sets the command line object

        Returns:

        """
        # Input path is different for legacy exes
        input_path = r"./Assets;." if not (self.legacy_exe or self.is_linux) else "./Assets"

        # Create the command line according to self. location of the model
        if self.use_embedded_python:
            self.command = CommandLine(f"Assets/{self.executable_name}", "--config config.json",  # noqa
                                       f"--input-path .", f"--dll-path ./Assets",  # noqa
                                       f"--python-script-path ./Assets/python")  # noqa
        else:
            self.command = CommandLine(f"Assets/{self.executable_name}", "--config config.json",  # noqa
                                       f"--input-path {input_path}", f"--dll-path ./Assets")  # noqa
