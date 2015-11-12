import os
from pkg_resources import resource_filename

import arcpy
import numpy

import nose.tools as nt
import numpy.testing as nptest
import tidegates.testing as tgtest
import mock

import tidegates
from tidegates import utils, toolbox


@nt.nottest
class MockResult(object):
    @staticmethod
    def getOutput(index):
        if index == 0:
            return resource_filename("tidegates.testing.input", "test_zones.shp")


@nt.nottest
class MockParam(object):
    def __init__(self, name, value):
        self.name = name
        self.valueAsText = value


class CheckToolbox_Mixin(object):
    mockMap = mock.Mock(spec=utils.EasyMapDoc)
    mockLayer = mock.Mock(spec=arcpy.mapping.Layer)
    mockUtils = mock.Mock(spec=utils)
    mxd = resource_filename("tidegates.testing.toolbox", "test.mxd")
    simple_shp = resource_filename("tidegates.testing.toolbox", "ZOI.shp")
    outfile = "output.shp"

    parameters = [
        MockParam('dem', 'path/to/dem'),
        MockParam('ID_column', 'GeoID'),
        MockParam('elevation', '7.8;8.9;9.2')
    ]

    parameter_dict = {
        'dem': 'path/to/dem',
        'ID_column': 'GeoID',
        'elevation': ['7.8', '8.9', '9.2']
    }

    def test_isLicensed(self):
        # every toolbox should be always licensed!
        nt.assert_true(self.tbx.isLicensed())

    def test_getParameterInfo(self):
        with mock.patch.object(self.tbx, '_params_as_list') as _pal:
            self.tbx.getParameterInfo()
            _pal.assert_called_once_with()

    def test_execute(self):
        messages = ['message1', 'message2']
        with mock.patch.object(self.tbx, 'main_execute') as _exe:
            self.tbx.execute(self.parameters, messages)
            _exe.assert_called_once_with(**self.parameter_dict)

    def test__set_parameter_dependency_single(self):
        self.tbx._set_parameter_dependency(
            self.tbx.ID_column,
            self.tbx.zones
        )

        nt.assert_list_equal(
            self.tbx.ID_column.parameterDependencies,
            [self.tbx.zones.name]
        )

    def test__set_parameter_dependency_many(self):
        self.tbx._set_parameter_dependency(
            self.tbx.ID_column,
            self.tbx.workspace,
            self.tbx.zones,
        )

        nt.assert_list_equal(
            self.tbx.ID_column.parameterDependencies,
            [self.tbx.workspace.name, self.tbx.zones.name]
        )

    def test__show_header(self):
        header = self.tbx._show_header("TEST MESSAGE", verbose=False)
        expected = "\nTEST MESSAGE\n------------"
        nt.assert_equal(header, expected)

    def test_add_result(self):
        with mock.patch.object(utils.EasyMapDoc, 'add_layer') as add_layer:
            ezmd = self.tbx._add_to_map(self.simple_shp, mxd=self.mxd)
            nt.assert_true(isinstance(ezmd, utils.EasyMapDoc))
            add_layer.assert_called_once_with(self.simple_shp)

    def test__add_scenario_columns_elev(self):
        with mock.patch.object(utils, 'add_field_with_value') as afwv:
            self.tbx._add_scenario_columns(MockResult, elev=5.0)
            afwv.assert_called_once_with(
                table=MockResult,
                field_name='flood_elev',
                field_value=5.0,
                msg="Adding 'flood_elev' field to ouput",
                verbose=True,
                asMessage=True
            )

    def test__add_scenario_columns_slr(self):
        with mock.patch.object(utils, 'add_field_with_value') as afwv:
            self.tbx._add_scenario_columns(MockResult, slr=5)
            afwv.assert_called_once_with(
                table=MockResult,
                field_name='slr',
                field_value=5,
                msg="Adding sea level rise field to ouput",
                verbose=True,
                asMessage=True
            )

    def test__add_scenario_columns_surge(self):
        with mock.patch.object(utils, 'add_field_with_value') as afwv:
            self.tbx._add_scenario_columns(MockResult, surge='TESTING')
            afwv.assert_called_once_with(
                table=MockResult,
                field_name="surge",
                field_value='TESTING',
                field_length=10,
                msg="Adding storm surge field to ouput",
                verbose=True,
                asMessage=True
            )

    def test_workspace(self):
        nt.assert_true(hasattr(self.tbx, 'workspace'))
        nt.assert_true(isinstance(self.tbx.workspace, arcpy.Parameter))
        nt.assert_equal(self.tbx.workspace.parameterType, "Required")
        nt.assert_equal(self.tbx.workspace.direction, "Input")
        nt.assert_equal(self.tbx.workspace.datatype, "Workspace")
        nt.assert_equal(self.tbx.workspace.name, 'workspace')

    def test__get_parameter_values_default(self):
        param_vals = self.tbx._get_parameter_values(self.parameters)
        expected = {
            'dem': 'path/to/dem',
            'ID_column': 'GeoID',
            'elevation': '7.8;8.9;9.2'
        }
        nt.assert_dict_equal(param_vals, expected)

    def test__get_parameter_values_multivals(self):
        param_vals = self.tbx._get_parameter_values(self.parameters, multivals='elevation')
        expected = {
            'dem': 'path/to/dem',
            'ID_column': 'GeoID',
            'elevation': ['7.8', '8.9', '9.2']
        }
        nt.assert_dict_equal(param_vals, expected)

    def test__prep_flooder_input_elev_only(self):
        elev, header, fname = self.tbx._prep_flooder_input(elev="7.8", flood_output="test.shp")
        nt.assert_equal(elev, 7.8)
        nt.assert_equal(header, "Analyzing flood elevation: 7.8 ft")
        nt.assert_equal(fname, 'test7_8.shp')

    def test__prep_flooder_input_surge_and_slr(self):
        elev, header, fname = self.tbx._prep_flooder_input(slr=2.5, surge='50yr', flood_output="test.shp")
        nt.assert_equal(elev, 12.1)
        nt.assert_equal(header, "Analyzing flood elevation: 12.1 ft (50yr, 2.5)")
        nt.assert_equal(fname, 'test12_1.shp')

    def test_dem(self):
        nt.assert_true(hasattr(self.tbx, 'dem'))
        nt.assert_true(isinstance(self.tbx.dem, arcpy.Parameter))
        nt.assert_equal(self.tbx.dem.parameterType, "Required")
        nt.assert_equal(self.tbx.dem.direction, "Input")
        nt.assert_equal(self.tbx.dem.datatype, "Raster Dataset")
        nt.assert_equal(self.tbx.dem.name, 'dem')

    def test_zones(self):
        nt.assert_true(hasattr(self.tbx, 'zones'))
        nt.assert_true(isinstance(self.tbx.zones, arcpy.Parameter))
        nt.assert_equal(self.tbx.zones.parameterType, "Required")
        nt.assert_equal(self.tbx.zones.direction, "Input")
        nt.assert_equal(self.tbx.zones.datatype, "Feature Class")
        nt.assert_equal(self.tbx.zones.name, 'zones')

    def test_ID_column(self):
        nt.assert_true(hasattr(self.tbx, 'ID_column'))
        nt.assert_true(isinstance(self.tbx.ID_column, arcpy.Parameter))
        nt.assert_equal(self.tbx.ID_column.parameterType, "Required")
        nt.assert_equal(self.tbx.ID_column.direction, "Input")
        nt.assert_equal(self.tbx.ID_column.datatype, "Field")
        nt.assert_equal(self.tbx.ID_column.name, 'ID_column')

    def test_flood_output(self):
        nt.assert_true(hasattr(self.tbx, 'flood_output'))
        nt.assert_true(isinstance(self.tbx.flood_output, arcpy.Parameter))
        nt.assert_equal(self.tbx.flood_output.parameterType, "Required")
        nt.assert_equal(self.tbx.flood_output.direction, "Input")
        nt.assert_equal(self.tbx.flood_output.datatype, "String")
        nt.assert_equal(self.tbx.flood_output.name, 'flood_output')

    def test_building_output(self):
        nt.assert_true(hasattr(self.tbx, 'building_output'))
        nt.assert_true(isinstance(self.tbx.building_output, arcpy.Parameter))
        nt.assert_equal(self.tbx.building_output.parameterType, "Optional")
        nt.assert_equal(self.tbx.building_output.direction, "Input")
        nt.assert_equal(self.tbx.building_output.datatype, "String")
        nt.assert_equal(self.tbx.building_output.name, 'building_output')

    def test_wetland_output(self):
        nt.assert_true(hasattr(self.tbx, 'wetland_output'))
        nt.assert_true(isinstance(self.tbx.wetland_output, arcpy.Parameter))
        nt.assert_equal(self.tbx.wetland_output.parameterType, "Optional")
        nt.assert_equal(self.tbx.wetland_output.direction, "Input")
        nt.assert_equal(self.tbx.wetland_output.datatype, "String")
        nt.assert_equal(self.tbx.wetland_output.name, 'wetland_output')

    def test_buildings(self):
        nt.assert_true(hasattr(self.tbx, 'buildings'))
        nt.assert_true(isinstance(self.tbx.buildings, arcpy.Parameter))
        nt.assert_equal(self.tbx.buildings.parameterType, "Optional")
        nt.assert_equal(self.tbx.buildings.direction, "Input")
        nt.assert_equal(self.tbx.buildings.datatype, "Feature Class")
        nt.assert_equal(self.tbx.buildings.name, 'buildings')

    def test_wetlands(self):
        nt.assert_true(hasattr(self.tbx, 'wetlands'))
        nt.assert_true(isinstance(self.tbx.wetlands, arcpy.Parameter))
        nt.assert_equal(self.tbx.wetlands.parameterType, "Optional")
        nt.assert_equal(self.tbx.wetlands.direction, "Input")
        nt.assert_equal(self.tbx.wetlands.datatype, "Feature Class")
        nt.assert_equal(self.tbx.wetlands.name, 'wetlands')

    def test__make_scenarios_elevation_list(self):
        expected = [
            {'elev': 7.8, 'surge_name': None, 'surge_elev': None, 'slr': None},
            {'elev': 8.6, 'surge_name': None, 'surge_elev': None, 'slr': None},
            {'elev': 9.2, 'surge_name': None, 'surge_elev': None, 'slr': None},
        ]

        test = self.tbx._make_scenarios(elevation=['7.8', '8.6', '9.2'])

        for ts, es in zip(test, expected):
            nt.assert_dict_equal(ts, es)

    def test__make_scenarios_elevation_scalar(self):
        expected = [
            {'elev': 7.8, 'surge_name': None, 'surge_elev': None, 'slr': None},
        ]

        test = self.tbx._make_scenarios(elevation='7.8')

        for ts, es in zip(test, expected):
            nt.assert_dict_equal(ts, es)

    def test__make_scenarios_no_elev(self):
        test = self.tbx._make_scenarios()

        for ts in test:
            nt.assert_true(ts['elev'] is None)
            nt.assert_true(ts['surge_name'] in toolbox.SURGES.keys())
            nt.assert_true(ts['surge_elev'] in toolbox.SURGES.values())
            nt.assert_true(ts['slr'] in toolbox.SEALEVELRISE)

    @nptest.dec.skipif(not tgtest.has_fiona)
    def test_finish_results_no_source(self):
        results = [
            resource_filename('tidegates.testing.finish_result', 'res1.shp'),
            resource_filename('tidegates.testing.finish_result', 'res2.shp'),
            resource_filename('tidegates.testing.finish_result', 'res3.shp')
        ]
        with utils.OverwriteState(True):
            self.tbx.finish_results(
                resource_filename('tidegates.testing.finish_result', 'finished_no_src.shp'),
                results,
                cleanup=False
            )

        tgtest.assert_shapefiles_are_close(
            resource_filename('tidegates.testing.finish_result', 'finished_no_src.shp'),
            resource_filename('tidegates.testing.finish_result', 'known_finished_no_src.shp'),
        )

    @nptest.dec.skipif(not tgtest.has_fiona)
    def test_finish_results_with_source(self):
        results = [
            resource_filename('tidegates.testing.finish_result', 'res1.shp'),
            resource_filename('tidegates.testing.finish_result', 'res2.shp'),
            resource_filename('tidegates.testing.finish_result', 'res3.shp')
        ]
        with utils.OverwriteState(True):
            self.tbx.finish_results(
                resource_filename('tidegates.testing.finish_result', 'finished_with_src.shp'),
                results,
                cleanup=False,
                sourcename=resource_filename('tidegates.testing.finish_result', 'source.shp')
            )

        tgtest.assert_shapefiles_are_close(
            resource_filename('tidegates.testing.finish_result', 'finished_with_src.shp'),
            resource_filename('tidegates.testing.finish_result', 'known_finished_with_src.shp'),
        )

    def test_analyze(self):
        ws = resource_filename('tidegates.testing', 'analyze')
        testdir = 'tidegates.testing.analyze'
        test_dem = resource_filename(testdir, 'dem.tif')
        test_zones = resource_filename(testdir, 'zones.shp')
        test_wetlands = resource_filename(testdir, 'wetlands.shp')
        test_buidlings = resource_filename(testdir, 'buildings.shp')
        output = resource_filename(testdir, 'flooding.shp')

        with utils.WorkSpace(ws), utils.OverwriteState(True):
            flood, wetland, building = self.tbx.analyze(
                elev=self.elev,
                slr=self.slr,
                surge=self.surge,
                flood_output=output,
                dem=test_dem,
                zones=test_zones,
                ID_column='GeoID',
                wetlands=test_wetlands,
                buildings=test_buidlings,
            )

        nt.assert_true(isinstance(flood, arcpy.mapping.Layer))
        nt.assert_equal(flood.dataSource, resource_filename(testdir, self.flood_output))
        nt.assert_true(isinstance(wetland, arcpy.mapping.Layer))
        nt.assert_true(isinstance(building, arcpy.mapping.Layer))

        tgtest.assert_shapefiles_are_close(
            resource_filename(testdir, self.flood_output),
            resource_filename(testdir, self.known_flood_output)
        )

    def test_analyze_no_optional_input(self):
        ws = resource_filename('tidegates.testing', 'analyze')
        testdir = 'tidegates.testing.analyze'
        test_dem = resource_filename(testdir, 'dem.tif')
        test_zones = resource_filename(testdir, 'zones.shp')
        test_wetlands = resource_filename(testdir, 'wetlands.shp')
        test_buidlings = resource_filename(testdir, 'buildings.shp')
        output = resource_filename(testdir, 'flooding_no_opts.shp')

        with utils.WorkSpace(ws), utils.OverwriteState(True):
            flood, wetland, building = self.tbx.analyze(
                elev=self.elev,
                slr=self.slr,
                surge=self.surge,
                flood_output=output,
                dem=test_dem,
                zones=test_zones,
                ID_column='GeoID',
                wetlands=None,
                buildings=None
            )

        nt.assert_true(isinstance(flood, arcpy.mapping.Layer))
        nt.assert_equal(flood.dataSource, resource_filename(testdir, self.flood_output_no_opts))
        nt.assert_true(wetland is None)
        nt.assert_true(building is None)

        tgtest.assert_shapefiles_are_close(
            resource_filename(testdir, self.flood_output_no_opts),
            resource_filename(testdir, self.known_flood_output_no_opts)
        )

    @mock.patch('tidegates.toolbox.SEALEVELRISE', [0, 1])
    @mock.patch('tidegates.toolbox.SURGES', {'MHHW': 4.0, '10yr': 8.0})
    def test_main_execute(self):
        with utils.OverwriteState(True), utils.WorkSpace(self.main_execute_ws):
            self.tbx.main_execute(
                zones='zones.shp',
                workspace=self.main_execute_ws,
                flood_output='test_floods.shp',
                wetland_output='test_wetlands.shp',
                building_output='test_buildings.shp',
                wetlands='wetlands.shp',
                buildings='buildings.shp',
                ID_column='GeoID',
                dem='dem.tif',
                elevation=self.elev_list
            )

            utils.cleanup_temp_results("tempraster")

        tgtest.assert_shapefiles_are_close(
            resource_filename(self.main_execute_dir, 'test_wetlands.shp'),
            resource_filename(self.main_execute_dir, 'known_wetlands.shp'),
        )

        tgtest.assert_shapefiles_are_close(
            resource_filename(self.main_execute_dir, 'test_floods.shp'),
            resource_filename(self.main_execute_dir, 'known_floods.shp'),
        )

        tgtest.assert_shapefiles_are_close(
            resource_filename(self.main_execute_dir, 'test_buildings.shp'),
            resource_filename(self.main_execute_dir, 'known_buildings.shp'),
        )

    @mock.patch('tidegates.toolbox.SEALEVELRISE', [0, 1])
    @mock.patch('tidegates.toolbox.SURGES', {'MHHW': 4.0, '10yr': 8.0})
    def test_main_execute_no_assets(self):
        with utils.OverwriteState(True), utils.WorkSpace(self.main_execute_ws):
            self.tbx.main_execute(
                zones='zones.shp',
                workspace=self.main_execute_ws,
                flood_output='test_floods_no_assets.shp',
                ID_column='GeoID',
                dem='dem.tif',
                elevation=self.elev_list
            )

            utils.cleanup_temp_results("tempraster")

        tgtest.assert_shapefiles_are_close(
            resource_filename(self.main_execute_dir, 'test_floods_no_assets.shp'),
            resource_filename(self.main_execute_dir, 'known_floods_no_assets.shp'),
        )


class Test_Flooder(CheckToolbox_Mixin):
    def setup(self):
        self.tbx = toolbox.Flooder()
        self.elev = 7.8
        self.elev_list = [6.8, 7.8, 9.8]
        self.surge = None
        self.slr = None
        self.flood_output = 'flooding7_8.shp'
        self.flood_output_no_opts = 'flooding_no_opts7_8.shp'
        self.known_flood_output = 'known_flooding7_8.shp'
        self.known_flood_output_no_opts = 'known_flooding_no_opts7_8.shp'
        self.main_execute_dir = 'tidegates.testing.execute_elev'
        self.main_execute_ws = resource_filename('tidegates.testing', 'execute_elev')

    def test_elevation(self):
        nt.assert_true(hasattr(self.tbx, 'elevation'))
        nt.assert_true(isinstance(self.tbx.elevation, arcpy.Parameter))
        nt.assert_equal(self.tbx.elevation.parameterType, "Required")
        nt.assert_equal(self.tbx.elevation.direction, "Input")
        nt.assert_equal(self.tbx.elevation.datatype, "Double")
        nt.assert_equal(self.tbx.elevation.name, 'elevation')

    def test_params_as_list(self):
        params = self.tbx._params_as_list()
        names = [str(p.name) for p in params]
        known_names = ['workspace', 'dem', 'zones', 'ID_column', 'elevation',
                       'flood_output', 'wetlands', 'wetland_output',
                       'buildings', 'building_output']
        nt.assert_list_equal(names, known_names)


class Test_StandardScenarios(CheckToolbox_Mixin):
    def setup(self):
        self.tbx = toolbox.StandardScenarios()
        self.elev = None
        self.elev_list = None
        self.surge = 'MHHW'
        self.slr = 2.5
        self.flood_output = 'flooding6_5.shp'
        self.flood_output_no_opts = 'flooding_no_opts6_5.shp'
        self.known_flood_output = 'known_flooding6_5.shp'
        self.known_flood_output_no_opts = 'known_flooding_no_opts6_5.shp'
        self.main_execute_dir = 'tidegates.testing.execute_std'
        self.main_execute_ws = resource_filename('tidegates.testing', 'execute_std')

    def test_params_as_list(self):
        params = self.tbx._params_as_list()
        names = [str(p.name) for p in params]
        known_names = ['workspace', 'dem', 'zones', 'ID_column',
                       'flood_output', 'wetlands', 'wetland_output',
                       'buildings', 'building_output']
        nt.assert_list_equal(names, known_names)
