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
        self.tools = [Flooder]


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

    @staticmethod
    def _set_parameter_dependency(downstream, *upstream):
        """ Set the dependecy of a arcpy.Parameter

        Parameters
        ----------
        downstream : arcpy.Parameter
            The Parameter that is reliant on an upstream parameter.
        upstream : acrpy.Parameters
            An arbitraty number of "upstream" parameters on which the
            "downstream" parameter depends.

        Returns
        -------
        None

        See Also
        --------
        http://goo.gl/HcR6WJ

        """

        downstream.parameterDependencies = [u.name for u in upstream]


class Flooder(BaseTool_Mixin):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "1 - Create Flood Scenarios"
        self.description = ""
        self.canRunInBackground = True

        self._workspace = None
        self._dem = None
        self._polygons = None
        self._tidegate_column = None
        self._elevation = None
        self._filename = None

    def updateParameters(self, parameters):
        """ Automatically called when any parameter is updated in the
        GUI.

        Flow is like this:
            1. User interacts with GUI, filling out some input element
            2. self.getParameterInfo is called
            3. Parameteter are fed to this method as a list

        """

        # tidegate_columns looks into the polygons layer to get a list of fields
        self._set_parameter_dependency(self.tidegate_column, self.polygons)

    @property
    def workspace(self):
        if self._workspace is None:
            self._workspace = arcpy.Parameter(
                displayName="Analysis WorkSpace",
                name='workspace',
                datatype="DEWorkspace",
                parameterType="Required",
                direction="Input"
            )
        return self._workspace

    @property
    def dem(self):
        if self._dem is None:
            self._dem = arcpy.Parameter(
                displayName="Digital Elevation Model",
                name="dem",
                datatype="DERasterDataset",
                parameterType="Required",
                direction="Input"
            )
        return self._dem

    @property
    def polygons(self):
        if self._polygons is None:
            self._polygons = arcpy.Parameter(
                displayName="Tidegate Zones of Influence",
                name="polygons",
                datatype="DEFeatureClass",
                parameterType="Required",
                direction="Input"
            )
        return self._polygons

    @property
    def tidegate_column(self):
        if self._tidegate_column is None:
            self._tidegate_column = arcpy.Parameter(
                displayName="Column with Tidegate IDs",
                name="tidegate_column",
                datatype="Field",
                parameterType="Required",
                direction="Input"
            )
            self._set_parameter_dependency(self.tidegate_column, self._polygons)
        return self._tidegate_column

    @property
    def elevation(self):
        if self._elevation is None:
            self._elevation = arcpy.Parameter(
                displayName="Water Surface Elevation",
                name="elevation",
                datatype="GPDouble",
                parameterType="Required",
                direction="Input",
                multiValue=False
            )
        return self._elevation

    @property
    def filename(self):
        if self._filename is None:
            self._filename = arcpy.Parameter(
                displayName="Output layer/filename",
                name="filename",
                datatype="GPString",
                parameterType="Optional",
                direction="Input"
            )
        return self._filename

    def getParameterInfo(self):
        """ Returns all parameter definitions"""
        params = [
            self.workspace,
            self.dem,
            self.polygons,
            self.tidegate_column,
            self.elevation,
            self.filename
        ]
        return params

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


""" ESRI Documentation
parameter types  http://resources.arcgis.com/en/help/main/10.2/index.html#/Defining_parameter_data_types_in_a_Python_toolbox/001500000035000000/

"""
