import os
from pkg_resources import resource_filename
import shutil
import glob

import numpy

import nose.tools as nt
from nose import with_setup
import numpy.testing as nptest
import tidegates.testing as tgtest

import arcpy

import tidegates
from tidegates import utils


def test_process_dem_and_zones():
    known_topo = numpy.array([
        [-999.0, 0.305, 0.610, 0.914, 1.219, 1.524, 1.829, 2.134,],
        [ 0.305, 0.610, 0.914, 1.219, 1.524, 1.829, 2.134, 2.438,],
        [ 0.610, 0.914, 1.219, 1.524, 1.829, 2.134, 2.438, 2.743,],
        [ 0.914, 1.219, 1.524, 1.829, 2.134, 2.438, 2.743, 3.048,],
        [ 1.219, 1.524, 1.829, 2.134, 2.438, 2.743, 3.048, 3.353,],
        [ 1.524, 1.829, 2.134, 2.438, 2.743, 3.048, 3.353, 3.658,],
    ])

    known_zones = numpy.array([
        [-999,    2,    2,    2,    2,    2,    2, -999],
        [-999,    2,    2,    2, -999,    2,    2, -999],
        [   1,    1,    1,    1, -999,    2,    2, -999],
        [   1,    1,    1,    1, -999,    2,    2, -999],
        [   1, -999,    1,    1,    2,    2,    2,    2],
        [-999, -999,    1,    1,    2,    2,    2,    2]
    ])

    known_cell_size = 8
    known_X, known_Y = 4, 22
    ws = resource_filename('tidegates.testing', 'process_dem_and_zones')
    with utils.WorkSpace(ws), utils.OverwriteState(True):
        ta, za, template = tidegates.process_dem_and_zones(
            dem='topo.tif',
            zones='zones.shp',
            ID_column='GeoID',
            cleanup=True,
            verbose=False
        )

    nptest.assert_array_almost_equal(ta, known_topo, decimal=3)
    nptest.assert_array_almost_equal(za, known_zones, decimal=3)
    nt.assert_equal(template.meanCellWidth, known_cell_size)
    nt.assert_equal(template.meanCellHeight, known_cell_size)
    nt.assert_equal(template.extent.lowerLeft.X, known_X)
    nt.assert_equal(template.extent.lowerLeft.Y, known_Y)


@nptest.dec.skipif(not tgtest.has_fiona)
def test_flood_area():
    topo = numpy.mgrid[:8, :8].sum(axis=0) * tidegates.METERS_PER_FOOT
    zones = numpy.array([
        [-1,  2,  2,  2,  2,  2,  2, -1,],
        [-1,  2,  2,  2, -1,  2,  2, -1,],
        [ 1,  1,  1,  1, -1,  2,  2, -1,],
        [ 1,  1,  1,  1, -1,  2,  2, -1,],
        [ 1, -1,  1,  1,  2,  2,  2,  2,],
        [-1, -1,  1,  1,  2,  2,  2,  2,],
        [-1, -1, -1, -1, -1, -1, -1, -1,],
        [-1, -1, -1, -1, -1, -1, -1, -1,]
    ])
    template = utils._Template(8, 4, 6)
    ws = resource_filename('tidegates.testing', 'flood_area')
    filename = 'test_flood_area_output.shp'
    with utils.WorkSpace(ws), utils.OverwriteState(True):
        floods = tidegates.flood_area(
            topo_array=topo,
            zones_array=zones,
            template=template,
            ID_column='GeoID',
            elevation_feet=5,
            filename=filename,
            cleanup=True,
            verbose=False,
        )

    nt.assert_true(isinstance(floods, arcpy.mapping.Layer))
    tgtest.assert_shapefiles_are_close(
        resource_filename('tidegates.testing.flood_area', 'known_flood_area_output.shp'),
        resource_filename('tidegates.testing.flood_area', filename)
    )

    utils.cleanup_temp_results(floods)


class Check_Impact_Mixin(object):
    def setup(self):
        self.orig_input = 'raw_flood_impacts.shp'
        self.input_name = 'flood_impacts'
        self.known_floods = os.path.join(self.workspace, 'known_flood_impacts.shp')
        self.known_wetlands = os.path.join(self.workspace, 'known_flooded_wetlands.shp')
        self.known_buildings = os.path.join(self.workspace, 'known_flooded_buildings.shp')
        self.wetlands = os.path.join(self.workspace, 'wetlands.shp')
        self.buildings = os.path.join(self.workspace, 'buildings.shp')
        self.floods = self.copy_shapefile(self.orig_input, self.input_name)

        self.known_floods_with_wtld = os.path.join(self.workspace, 'known_flood_impacts_with_wtld.shp')
        self.known_floods_with_bldg = os.path.join(self.workspace, 'known_flood_impacts_with_bldg.shp')

    def teardown(self):
        pass

    @nt.nottest
    def copy_shapefile(self, src_name, dst_name):
        shapename, _ = os.path.splitext(src_name)
        files = glob.glob(os.path.join(self.workspace, shapename) + '.*')
        for f in files:
            _, ext = os.path.splitext(f)
            shutil.copy(
                os.path.join(self.workspace, f),
                os.path.join(self.workspace, dst_name + ext)
            )

        return os.path.join(self.workspace, dst_name + '.shp')


class Test_assess_impact(Check_Impact_Mixin):
    workspace = resource_filename('tidegates.testing', 'assess_impact')

    @nptest.dec.skipif(not tgtest.has_fiona)
    def test_fxn(self):

        with utils.WorkSpace(self.workspace), utils.OverwriteState(True):
            floodslyr, wetlandslyr, buildingslyr = tidegates.assess_impact(
                floods_path=self.floods,
                flood_idcol='GeoID',
                wetlands_path=self.wetlands,
                buildings_path=self.buildings,
                buildings_output=os.path.join(self.workspace, 'flooded_buildings.shp'),
                wetlands_output=os.path.join(self.workspace, 'flooded_wetlands.shp'),
                cleanup=False,
                verbose=False,
            )

            nt.assert_true(isinstance(floodslyr, arcpy.mapping.Layer))
            tgtest.assert_shapefiles_are_close(floodslyr.dataSource, self.known_floods)

            nt.assert_true(isinstance(wetlandslyr, arcpy.mapping.Layer))
            tgtest.assert_shapefiles_are_close(wetlandslyr.dataSource, self.known_wetlands)

            nt.assert_true(isinstance(buildingslyr, arcpy.mapping.Layer))
            tgtest.assert_shapefiles_are_close(buildingslyr.dataSource, self.known_buildings)

        with utils.WorkSpace(self.workspace):
            utils.cleanup_temp_results(
                self.floods,
                'flooded_buildings.shp',
                'flooded_wetlands.shp',
                '_temp_flooded_wetlands.shp'
            )


class Test_area_of_impacts(Check_Impact_Mixin):
    workspace = resource_filename('tidegates.testing', 'area_of_impacts')

    @nptest.dec.skipif(not tgtest.has_fiona)
    def test_wetlands(self):
        with utils.WorkSpace(self.workspace), utils.OverwriteState(True):
            outputlayer = tidegates.area_of_impacts(
                floods_path=self.floods,
                flood_idcol='GeoID',
                assets_input=self.wetlands,
                fieldname='wtld_area',
                assets_output=os.path.join(self.workspace, 'flooded_wetlands.shp'),
                cleanup=False,
                verbose=False,
            )

            nt.assert_true(isinstance(outputlayer, arcpy.mapping.Layer))
            tgtest.assert_shapefiles_are_close(outputlayer.dataSource, self.known_wetlands)

            tgtest.assert_shapefiles_are_close(self.floods, self.known_floods_with_wtld)

        with utils.WorkSpace(self.workspace):
            utils.cleanup_temp_results(
                self.floods,
                'flooded_wetlands.shp',
                '_temp_flooded_wetlands.shp'
            )

    @nptest.dec.skipif(not tgtest.has_fiona)
    def test_buildings(self):

        with utils.WorkSpace(self.workspace), utils.OverwriteState(True):
            outputlayer = tidegates.area_of_impacts(
                floods_path=self.floods,
                flood_idcol='GeoID',
                assets_input=self.buildings,
                fieldname='bldg_area',
                assets_output=os.path.join(self.workspace, 'flooded_buildings.shp'),
                cleanup=False,
                verbose=False,
            )

            nt.assert_true(isinstance(outputlayer, arcpy.mapping.Layer))
            tgtest.assert_shapefiles_are_close(outputlayer.dataSource, self.known_buildings)

        with utils.WorkSpace(self.workspace):
            utils.cleanup_temp_results(
                self.floods,
                'flooded_buildings.shp',
                '_temp_flooded_buildings.shp'
            )


class Test_count_of_impacts(Check_Impact_Mixin):
    workspace = resource_filename('tidegates.testing', 'count_of_impacts')

    @nptest.dec.skipif(not tgtest.has_fiona)
    def test_wetlands(self):
        with utils.WorkSpace(self.workspace), utils.OverwriteState(True):
            outputlayer = tidegates.count_of_impacts(
                floods_path=self.floods,
                flood_idcol='GeoID',
                fieldname='wetlands',
                assets_input=self.wetlands,
                asset_idcol='WETCODE',
                assets_output=os.path.join(self.workspace, 'flooded_wetlands.shp'),
                verbose=False,
            )

            nt.assert_true(isinstance(outputlayer, arcpy.mapping.Layer))
            tgtest.assert_shapefiles_are_close(outputlayer.dataSource, self.known_wetlands)

            tgtest.assert_shapefiles_are_close(self.floods, self.known_floods_with_wtld)

        with utils.WorkSpace(self.workspace):
            utils.cleanup_temp_results(
                self.floods,
                'flooded_wetlands.shp',
                '_temp_flooded_wetlands.shp'
            )


    @nptest.dec.skipif(not tgtest.has_fiona)
    def test_buildings(self):

        with utils.WorkSpace(self.workspace), utils.OverwriteState(True):
            outputlayer = tidegates.count_of_impacts(
                floods_path=self.floods,
                flood_idcol='GeoID',
                fieldname='bldg',
                assets_input=self.buildings,
                asset_idcol='STRUCT_ID',
                assets_output=os.path.join(self.workspace, 'flooded_buildings.shp'),
                verbose=False,
            )

            nt.assert_true(isinstance(outputlayer, arcpy.mapping.Layer))
            tgtest.assert_shapefiles_are_close(outputlayer.dataSource, self.known_buildings)

            tgtest.assert_shapefiles_are_close(self.floods, self.known_floods_with_bldg)

        with utils.WorkSpace(self.workspace):
            utils.cleanup_temp_results(
                self.floods,
                'flooded_buildings.shp',
                '_temp_flooded_buildings.shp'
            )
