import os
import sys
import glob
import datetime

import numpy

import arcpy

from tidegates import tidegates

METERS_PER_FEET = 0.3048

MHHW = 4  * METERS_PER_FEET # GUESS
SEALEVELRISE = numpy.arange(7) * METERS_PER_FEET
SURGES = {
    'MHHW' :   4.0 * METERS_PER_FEET, # no storm surge
    '10-yr':   8.0 * METERS_PER_FEET, #  10-yr (approx)
    '25-yr':   8.5 * METERS_PER_FEET, #  25-yr (guess)
    '50-yr':   9.6 * METERS_PER_FEET, #  50-yr (approx)
    '100-yr': 10.5 * METERS_PER_FEET, # 100-yr (guess
}


class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "pytidegates"
        self.alias = "pytidegates"

        # List of tool classes associated with this toolbox
        self.tools = [Flooder, Assessor]


class BaseTool_Mixin(object):
    def getParameterInfo(self):
        """Define parameter definitions"""
        params = None
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return


class Flooder(BaseTool_Mixin):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "1 - Create Flood Scenarios"
        self.description = ""
        self.canRunInBackground = True

    def getParameterInfo(self):
        """Define parameter definitions"""

        workspace = arcpy.Parameter(
            displayName="Analysis WorkSpace",
            name='workspace',
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input"
        )

        dem = arcpy.Parameter(
            displayName="Digital Elevation Model",
            name="dem",
            datatype="DERasterDataset",
            parameterType="Required",
            direction="Input"
        )

        polygons = arcpy.Parameter(
            displayName="Tidegate Zones of Influence",
            name="polygons",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Input"
        )

        tidegate_column = arcpy.Parameter(
            displayName="Column with Tidegate IDs",
            name="tidegate_column",
            datatype="Field",
            parameterType="Required",
            direction="Input"
        )

        elevation = arcpy.Parameter(
            displayName="Water Surface Elevation",
            name="elevation",
            datatype="GPDouble",
            parameterType="Required",
            direction="Input"
        )

        filename = arcpy.Parameter(
            displayName="Output layer/filename",
            name="filename",
            datatype="GPString",
            parameterType="Optional",
            direction="Input"
        )

        floods = arcpy.Parameter(
            displayName="Output layer/filename",
            name="floods",
            datatype="DEFeatureClass",
            parameterType="Derived",
            direction="Output"
        )

        return [workspace, dem, polygons, tidegate_column, elevation, filename, floods]

    def execute(self, parameters, messages):
        """The source code of the tool."""

        workspace = parameters[0].valueAsText
        dem = parameters[1].valueAsText
        polygons = parameters[2].valueAsText
        tidegate_column = parameters[3].valueAsText
        elevation = parameters[4].value
        filename = parameters[5].valueAsText

        with tidegates.utils.WorkSpace(workspace):
            return tidegates.flood_area(dem, polygons, tidegate_column, elevation, filename=filename)


class Assessor(BaseTool_Mixin):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "2 - Assess Flood Impacts"
        self.description = ""
        self.canRunInBackground = True

    def execute(self, parameters, messages):
        """The source code of the tool."""
        return tidegate.assess_impact(*parameters)
