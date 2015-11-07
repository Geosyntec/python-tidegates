import os
import sys
import glob
import datetime
from textwrap import dedent

import arcpy
import numpy

import tidegates
from tidegates import utils


# ALL ELEVATIONS IN FEET
SEALEVELRISE = numpy.arange(7)
SURGES = {
    'MHHW':   4.0,
    '10yr':   8.0,
    '50yr':   9.6,
    '100yr': 10.5,
}


class BaseFlooder_Mixin(object):
    def __init__(self):
        #std attributes
        self.canRunInBackground = True

        # lazy properties
        self._workspace = None
        self._dem = None
        self._polygons = None
        self._ID_column = None
        self._flood_output = None
        self._building_output = None
        self._wetland_output = None
        self._wetlands = None
        self._buildings = None

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateMessages(self, parameters): # pragma: no cover
        """Modify the messages created by internal validation for each
        parameter of the tool.  This method is called after internal
        validation."""
        return

    def updateParameters(self, parameters): # pragma: no cover
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
    def _show_header(title, verbose=True):
        underline = ''.join(['-'] * len(title))
        header = '\n{}\n{}'.format(title, underline)
        utils._status(header, verbose=verbose, asMessage=True, addTab=False)
        return header

    @staticmethod
    def _add_results_to_map(mapname, filename):
        ezmd = utils.EasyMapDoc(mapname)
        if ezmd.mapdoc is not None:
            ezmd.add_layer(filename)

        return ezmd

    @staticmethod
    def _add_scenario_columns(layer, elev=None, surge=None, slr=None):
        if elev is not None:
            utils.add_field_with_value(
                table=layer,
                field_name="flood_elev",
                field_value=float(elev),
                msg="Adding 'flood_elev' field to ouput",
                verbose=True,
                asMessage=True
            )

        if surge is not None:
            utils.add_field_with_value(
                table=layer,
                field_name="surge",
                field_value=str(surge),
                field_length=10,
                msg="Adding storm surge field to ouput",
                verbose=True,
                asMessage=True
            )

        if slr is not None:
            utils.add_field_with_value(
                table=layer,
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

    @staticmethod
    def _get_parameter_values(parameters, multivals=None):
        if multivals is None:
            multivals = []
        elif numpy.isscalar(multivals):
            multivals = [multivals]

        params = {}
        for p in parameters:
            value = p.valueAsText
            if p.name in multivals:
                value = value.split(';')
            params[p.name] = value

        return params

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
    def ID_column(self):
        if self._ID_column is None:
            self._ID_column = arcpy.Parameter(
                displayName="Column with Tidegate IDs",
                name="ID_column",
                datatype="Field",
                parameterType="Required",
                direction="Input",
                multiValue=False
            )
            self._set_parameter_dependency(self._ID_column, self.polygons)
        return self._ID_column

    @property
    def flood_output(self):
        """ Where the flooded areas for each scenario will be saved.
        """
        if self._flood_output is None:
            self._flood_output = arcpy.Parameter(
                displayName="Output floods layer/filename",
                name="flood_output",
                datatype="GPString",
                parameterType="Required",
                direction="Input"
            )
        return self._flood_output

    @property
    def building_output(self):
        """ Where the flooded buildings for each scenario will be saved.
        """
        if self._building_output is None:
            self._building_output = arcpy.Parameter(
                displayName="Output layer/filename of impacted buildings",
                name="building_output",
                datatype="GPString",
                parameterType="Optional",
                direction="Input"
            )
        return self._building_output

    @property
    def wetland_output(self):
        """ Where the flooded wetlands for each scenario will be saved.
        """
        if self._wetland_output is None:
            self._wetland_output = arcpy.Parameter(
                displayName="Output layer/filename of impacted wetlands",
                name="wetland_output",
                datatype="GPString",
                parameterType="Optional",
                direction="Input"
            )
        return self._wetland_output

    @property
    def wetlands(self):
        if self._wetlands is None:
            self._wetlands = arcpy.Parameter(
                displayName="Wetlands",
                name="wetlands",
                datatype="DEFeatureClass",
                parameterType="Optional",
                direction="Input",
                multiValue=False
            )
            self._set_parameter_dependency(self._wetlands, self.workspace)
        return self._wetlands

    @property
    def buildings(self):
        if self._buildings is None:
            self._buildings = arcpy.Parameter(
                displayName="Buildings footprints",
                name="buildings",
                datatype="DEFeatureClass",
                parameterType="Optional",
                direction="Input",
                multiValue=False
            )
            self._set_parameter_dependency(self._buildings, self.workspace)
        return self._buildings

    def _do_flood(self, dem, poly, idcol, elev, filename, surge=None, slr=None):
        res = tidegates.flood_area(
            dem=dem,
            polygons=poly,
            ID_column=idcol,
            elevation_feet=elev,
            filename=flood_output,
            verbose=True,
            asMessage=True
        )
        self._add_scenario_columns(flooded_polygons, elev=elev, surge=surge, slr=slr)

        return flooded_polygons

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

    @staticmethod
    def _prep_elevation_and_filename(elev_string, filename):
        basename, ext = os.path.splitext(filename)
        fname = basename + elev_string.replace('.', '_') + ext
        elevation = float(elev_string)
        title = "Analyzing flood elevation: {} ft".format(elevation)

        return elevation, title, fname

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

        params = [
            self.workspace,
            self.dem,
            self.polygons,
            self.ID_column,
            self.elevation,
            self.flood_output,
            self.wetlands,
            self.wetland_output,
            self.buildings,
            self.building_output,
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
                header = self._show_header(base_msg)
                res = self._do_flood(dem, polygons, id_col, elev)
                results.append(res.getOutput(0))

        arcpy.management.Merge(results, filename)
        ezmd = self._add_results_to_map("CURRENT", filename)

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

    @staticmethod
    def _prep_elevation_and_filename(surge, slr, filename):
        basename, ext = os.path.splitext(filename)
        elevation = float(slr + SURGES[surge])
        fname = basename + str(elevation).replace('.', '_') + ext
        title = "Analyzing flood elevation: {} ft ({}, {})".format(elevation, surge, slr)

        return elevation, title, fname

        params = [
            self.workspace,
            self.dem,
            self.polygons,
            self.ID_column,
            self.flood_output,
            self.wetlands,
            self.wetland_output,
            self.buildings,
            self.building_output,
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
                    header = self._show_header(base_msg)
                    res = self._do_flood(dem, polygons, id_col, elev, surge=surge, slr=slr)
                    results.append(res.getOutput(0))

        arcpy.management.Merge(results, filename)
        ezmd = self._add_results_to_map("CURRENT", filename)

        return results
