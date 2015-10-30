import arcpy
from tidegates.toolbox import Flooder, StandardScenarios


class Toolbox(object):
    def __init__(self):
        """ Python-Tidegates: Analyze flooding behind tidegates under
        various sea-level rise as storm-surge scenarios.

        """

        self.label = "Python-Tidegates"
        self.alias = "python-tidegates"

        # List of tool classes associated with this toolbox
        self.tools = [Flooder, StandardScenarios]
