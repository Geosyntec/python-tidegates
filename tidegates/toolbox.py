import os
import sys
import glob
import datetime
from textwrap import dedent

import arcpy
import numpy

import tidegates
from tidegates import utils


SEALEVELRISE = numpy.arange(7) # FEET
SURGES = {
    'MHHW' :   4.0, # FEET
    '10-yr':   8.0, # FEET
    #'25-yr':   8.5, # FEET
    '50-yr':   9.6, # FEET
    '100-yr': 10.5, # FEET
}


class BaseFlooder_Mixin(object):
    def __init__(self):
        #std attributes
        self.canRunInBackground = True

        # lazy properties
        self._workspace = None
        self._dem = None
        self._polygons = None
        self._tidegate_column = None
        self._filename = None

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each
        parameter of the tool.  This method is called after internal
        validation."""
        return

    def updateParameters(self, parameters):
        """ Automatically called when any parameter is updated in the
        GUI.

        Flow is like this:
            1. User interacts with GUI, filling out some input element
            2. self.getParameterInfo is called
            3. Parameteter are fed to this method as a list

        """
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

    @staticmethod
    def _show_header(base_msg):
        underline = ''.join(['-'] * len(base_msg))
        header = '\n{}\n{}'.format(base_msg, underline)
        utils._status(header, verbose=True, asMessage=True, addTab=False)

    @staticmethod
    def _add_results_to_map(mapname, filename):
        ezmd = utils.EasyMapDoc(mapname)
        if ezmd.mapdoc is not None:
            ezmd.add_layer(filename)

    @staticmethod
    def _add_scenario_columns(result, elev=None, surge=None, slr=None):
        if elev is not None:
            utils.add_field_with_value(
                table=result.getOutput(0),
                field_name="flood_elev",
                field_value=float(elev),
                msg="Adding 'flood_elev' field to ouput",
                verbose=True,
                asMessage=True
            )

        if surge is not None:
            utils.add_field_with_value(
                table=result.getOutput(0),
                field_name="surge",
                field_value=str(surge),
                field_length=10,
                msg="Adding storm surge field to ouput",
                verbose=True,
                asMessage=True
            )

        if slr is not None:
            utils.add_field_with_value(
                table=result.getOutput(0),
                field_name="slr",
                field_value=int(slr),
                msg="Adding sea level rise field to ouput",
                verbose=True,
                asMessage=True
            )

    @property
    def workspace(self):
        if self._workspace is None:
            self._workspace = arcpy.Parameter(
                displayName="Analysis WorkSpace",
                name='workspace',
                datatype="DEWorkspace",
                parameterType="Required",
                direction="Input",
                multiValue=False
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
                direction="Input",
                multiValue=False
            )
            self._set_parameter_dependency(self._dem, self.workspace)
        return self._dem

    @property
    def polygons(self):
        if self._polygons is None:
            self._polygons = arcpy.Parameter(
                displayName="Tidegate Zones of Influence",
                name="polygons",
                datatype="DEFeatureClass",
                parameterType="Required",
                direction="Input",
                multiValue=False
            )
            self._set_parameter_dependency(self._polygons, self.workspace)
        return self._polygons

    @property
    def filename(self):
        if self._filename is None:
            self._filename = arcpy.Parameter(
                displayName="Output layer/filename",
                name="filename",
                datatype="GPString",
                parameterType="Required",
                direction="Input"
            )
        return self._filename

    @property
    def tidegate_column(self):
        if self._tidegate_column is None:
            self._tidegate_column = arcpy.Parameter(
                displayName="Column with Tidegate IDs",
                name="tidegate_column",
                datatype="Field",
                parameterType="Required",
                direction="Input",
                multiValue=False
            )
            self._set_parameter_dependency(self._tidegate_column, self.polygons)
        return self._tidegate_column

    def _do_flood(self, dem, poly, idcol, elev, surge=None, slr=None):
        res = tidegates.flood_area(
            dem=dem,
            polygons=poly,
            tidegate_column=idcol,
            elevation_feet=elev,
            filename=None,
            verbose=True,
            asMessage=True
        )
        self._add_scenario_columns(res, elev=elev, surge=surge, slr=slr)

        return res


class Flooder(BaseFlooder_Mixin):
    def __init__(self):
        # std attributes
        super(Flooder, self).__init__()
        self.label = "1 - Create Flood Scenarios"
        self.description = dedent("""
        Allows the user to create a custom flooding scenario given the
        following:
            - A DEM of the coastal area
            - A polygon layer describing the zones of influence of each
              tidegate
        """)

        # lazy properties
        self._elevation = None

    @property
    def elevation(self):
        if self._elevation is None:
            self._elevation = arcpy.Parameter(
                displayName="Water Surface Elevation",
                name="elevation",
                datatype="GPDouble",
                parameterType="Required",
                direction="Input",
                multiValue=True
            )
        return self._elevation

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
        id_col = parameters[3].valueAsText
        elevation = parameters[4].valueAsText.split(';')
        filename = parameters[5].valueAsText

        results = []
        with utils.WorkSpace(workspace):
            for _elev in elevation:
                elev = float(_elev)
                base_msg = "Analyzing flood elevation: {} ft".format(elev)
                self._show_header(base_msg)
                res = self._do_flood(dem, polygons, id_col, elev)
                results.append(res.getOutput(0))

        arcpy.management.Merge(results, filename)
        self._add_results_to_map("CURRENT", filename)

        return results


class StandardScenarios(BaseFlooder_Mixin):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        # std attributes
        super(StandardScenarios, self).__init__()
        self.label = "2 - Evaluate all standard scenarios"

        self.description = dedent("""
        Allows the user to recreate the standard scenarios with their
        own input.

        The standard scenarios are each combination of storm surges
        (MHHW, 10-yr, 50-yr, 100-yr) and sea level rise up to 6 feet in
        1-ft increments.
        """)

    def getParameterInfo(self):
        """ Returns all parameter definitions"""
        params = [
            self.workspace,
            self.dem,
            self.polygons,
            self.tidegate_column,
            self.filename
        ]
        return params

    def execute(self, parameters, messages):
        """The source code of the tool."""

        workspace = parameters[0].valueAsText
        dem = parameters[1].valueAsText
        polygons = parameters[2].valueAsText
        id_col = parameters[3].valueAsText
        filename = parameters[4].valueAsText

        results = []
        with utils.WorkSpace(workspace):
            for surge, surge_elev in SURGES.items():
                for slr in SEALEVELRISE:
                    elev = surge_elev + slr
                    base_msg = "Analyzing Storm Surge ({}) + SLR ({}) = {} ft".format(surge, slr, elev)
                    self._show_header(base_msg)
                    res = self._do_flood(dem, polygons, id_col, elev, surge=surge, slr=slr)
                    results.append(res.getOutput(0))

        arcpy.management.Merge(results, filename)
        self._add_results_to_map("CURRENT", filename)

        return results
