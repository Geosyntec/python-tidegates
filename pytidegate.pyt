import os
import sys
import glob
import datetime

import numpy

import arcpy

import tidegates


class Toolbox(object):
    def __init__(self):
        """ Python-Tidegates: Analyze flooding behind tidegates under
        various sea-level rise as storm-surge scenarios.

        """

        self.label = "pytidegates"
        self.alias = "pytidegates"

        # List of tool classes associated with this toolbox
        self.tools = [Flooder, Assessor]


class BaseTool_Mixin(object):
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
            direction="Input",
            multiValue=False
        )

        filename = arcpy.Parameter(
            displayName="Output layer/filename",
            name="filename",
            datatype="GPString",
            parameterType="Optional",
            direction="Input"
        )

        # floods = arcpy.Parameter(
        #     displayName="Output layer/filename",
        #     name="floods",
        #     datatype="DEFeatureClass",
        #     parameterType="Derived",
        #     direction="Output"
        # )

        return [workspace, dem, polygons, tidegate_column, elevation, filename]

    def execute(self, parameters, messages):
        """The source code of the tool."""

        workspace = parameters[0].valueAsText
        dem = parameters[1].valueAsText
        polygons = parameters[2].valueAsText
        tidegate_column = parameters[3].valueAsText
        elevation = parameters[4].value
        filename = parameters[5].valueAsText

        tidegates.utils.progress_print("""
            workspace: {}
            dem: {}
            polygons: {}
            tidegate_column: {}
            elevation: {}
            filename: {}
        """.format(workspace, dem, polygons, tidegate_column, elevation, filename))

        with tidegates.utils.WorkSpace(workspace):
            x = tidegates.flood_area(
                dem,
                polygons,
                tidegate_column,
                elevation,
                filename=filename,
                verbose=True,
                asMessage=True
            )

        return x



class Assessor(BaseTool_Mixin):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "2 - Assess Flood Impacts"
        self.description = ""
        self.canRunInBackground = True

    def execute(self, parameters, messages):
        """The source code of the tool."""
        return tidegate.assess_impact(*parameters)


""" ESRI Documentation
parameter types  http://resources.arcgis.com/en/help/main/10.2/index.html#/Defining_parameter_data_types_in_a_Python_toolbox/001500000035000000/

"""
