import os
from pkg_resources import resource_filename

import nose.tools as nt
import numpy.testing as nptest
import tidegates.testing as tgtest
import arcpy

import tidegates
from tidegates import utils


@nptest.dec.skipif(not tgtest.has_fiona)
def test_flood_area():
    ws = resource_filename('tidegates.testing', 'flood_area')
    with utils.WorkSpace(ws), utils.OverwriteState(True):
        filename = 'test_flood_area_output.shp'
        floods = tidegates.flood_area(
            dem='test_dem.tif',
            zones='test_zones.shp',
            ID_column='GeoID',
            elevation_feet=7.8,
            filename=filename,
            cleanup=True,
            verbose=True,
            asMessage=True,
        )

    nt.assert_true(isinstance(floods, arcpy.mapping.Layer))
    tgtest.assert_shapefiles_are_close(
        resource_filename('tidegates.testing.flood_area', 'known_flood_area_output.shp'),
        resource_filename('tidegates.testing.flood_area', filename)
    )

    utils.cleanup_temp_results(floods)


@nptest.dec.skipif(not tgtest.has_fiona)
def test_assess_impact():
    ws = resource_filename('tidegates.testing', 'assess_impact')
    floods = os.path.join(ws, 'flood_impacts.shp')
    known = os.path.join(ws, 'known_flood_impacts.shp')
    wetlands = os.path.join(ws, 'wetlands.shp')
    buildings = os.path.join(ws, 'buildings.shp')
    with utils.WorkSpace(ws), utils.OverwriteState(True):
        floodslyr, wetlandslyr, buildingslyr = tidegates.assess_impact(
            floods_path=floods,
            ID_column='GeoID',
            wetlands_path=wetlands,
            buildings_path=buildings,
            buildings_output='flooded_buildings.shp',
            wetlands_output='flooded_wetlands.shp',
            cleanup=True,
        )

        nt.assert_true(isinstance(floodslyr, arcpy.mapping.Layer))
        nt.assert_true(isinstance(wetlandslyr, arcpy.mapping.Layer))
        nt.assert_true(isinstance(buildingslyr, arcpy.mapping.Layer))
        tgtest.assert_shapefiles_are_close(floodslyr.dataSource, known)

        utils.cleanup_temp_results(
            wetlandslyr,
            buildingslyr,
            os.path.join(ws, '_temp_flooded_wetlands.shp')
        )


@nptest.dec.skipif(not tgtest.has_fiona)
def test_area_of_impacts_wetlands():
    ws = resource_filename('tidegates.testing', 'impact_to_wetlands')
    floods = 'flood_impacts.shp'
    known = 'known_flooded_wetlands.shp'
    wetlands = 'wetlands.shp'
    flooded_output = 'output_flooded_wetlands.shp'
    with utils.WorkSpace(ws), utils.OverwriteState(True):
        flooded_wetlands = tidegates.area_of_impacts(
            floods_path=floods,
            flood_idcol='GeoID',
            assets_input=wetlands,
            assets_output=flooded_output,
            cleanup=True
        )

        nt.assert_true(isinstance(flooded_wetlands, arcpy.mapping.Layer))
        tgtest.assert_shapefiles_are_close(
            resource_filename('tidegates.testing.impact_to_wetlands', 'output_flooded_wetlands.shp'),
            resource_filename('tidegates.testing.impact_to_wetlands', 'known_flooded_wetlands.shp')
        )

        utils.cleanup_temp_results(flooded_wetlands)


@nptest.dec.skipif(not tgtest.has_fiona)
def test_count_of_impacts_buildings():
    ws = resource_filename('tidegates.testing', 'impact_to_buildings')
    floods = 'flood_impacts.shp'
    known = 'known_flooded_buildings.shp'
    buildings = 'buildings.shp'
    flooded_output = 'output_flooded_buildings.shp'
    with utils.WorkSpace(ws), utils.OverwriteState(True):
        flooded_buildings = tidegates.count_of_impacts(
            floods_path=floods,
            flood_idcol='GeoID',
            assets_input=buildings,
            assets_output=flooded_output,
        )

    nt.assert_true(isinstance(flooded_buildings, arcpy.mapping.Layer))
    tgtest.assert_shapefiles_are_close(
        resource_filename('tidegates.testing.impact_to_buildings', flooded_output),
        resource_filename('tidegates.testing.impact_to_buildings', known)
    )

    utils.cleanup_temp_results(flooded_output)
