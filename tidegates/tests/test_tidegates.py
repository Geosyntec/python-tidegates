import os
from pkg_resources import resource_filename

import nose.tools as nt
import numpy.testing as nptest
import tidegates.testing as tgtest
import arcpy

from tidegates import tidegates, utils


@nptest.dec.skipif(not tgtest.has_fiona)
def test_flood_area():
    ws = resource_filename("tidegates", "testing")
    with utils.WorkSpace(ws), utils.OverwriteState(True):
        filename = os.path.join("output", "test_flood_area_output.shp")
        floods = tidegates.flood_area(
            dem=os.path.join('input', 'test_dem.tif'),
            polygons=os.path.join('input', 'test_zones.shp'),
            ID_column="GeoID",
            elevation_feet=7.8,
            filename=filename,
            verbose=False
        )

    nt.assert_true(isinstance(floods, arcpy.mapping.Layer))
    tgtest.assert_shapefiles_are_close(
        resource_filename("tidegates.testing.known", "known_flood_area_output.shp"),
        resource_filename("tidegates.testing", filename)
    )

    utils.cleanup_temp_results(floods)


@nptest.dec.skipif(not tgtest.has_fiona)
def test_assess_impact():
    ws = resource_filename("tidegates", "testing")
    floods = r"output\flood_impacts.shp"
    known = r"known\flood_impacts.shp"
    wetlands = r"input\test_wetlands.shp"
    buildings = r"input\buildings.shp"
    with utils.WorkSpace(ws), utils.OverwriteState(True):
        floods, wetlands, buildings = tidegates.assess_impact(
            floods_path=floods,
            ID_column="GeoID",
            wetlands_path=wetlands,
            buildings_path=buildings,
            buildings_output=r"output\flooded_buildings.shp",
            wetlands_output=r"output\flooded_wetlands.shp",
            cleanup=True,
        )

    nt.assert_true(isinstance(floods, arcpy.mapping.Layer))
    nt.assert_true(isinstance(wetlands, arcpy.mapping.Layer))
    nt.assert_true(isinstance(buildings, arcpy.mapping.Layer))
    tgtest.assert_shapefiles_are_close(
        resource_filename("tidegates.testing.output", "flood_impacts.shp"),
        resource_filename("tidegates.testing.known", "flood_impacts.shp")
    )

    utils.cleanup_temp_results(
        r"output\flooded_buildings.shp",
        r"output\flooded_wetlands.shp"
    )


@nptest.dec.skipif(not tgtest.has_fiona)
def test__impact_to_wetlands():
    ws = resource_filename("tidegates", "testing")
    floods = r"output\flood_impacts.shp"
    known = r"known\flooded_wetlands.shp"
    wetlands = r"input\test_wetlands.shp"
    flooded_output = r"output\flooded_wetlands.shp"
    with utils.WorkSpace(ws), utils.OverwriteState(True):
        flooded_wetlands = tidegates._impact_to_wetlands(
            floods_path=floods,
            ID_column="GeoID",
            wetlands_path=wetlands,
            wetlands_output=flooded_output,
        )

    nt.assert_true(isinstance(flooded_wetlands, arcpy.mapping.Layer))
    tgtest.assert_shapefiles_are_close(
        resource_filename("tidegates.testing.output", "flooded_wetlands.shp"),
        resource_filename("tidegates.testing.known", "flooded_wetlands.shp")
    )

    utils.cleanup_temp_results(flooded_output)


@nptest.dec.skipif(not tgtest.has_fiona)
def test__impact_to_buildings():
    ws = resource_filename("tidegates", "testing")
    floods = r"output\flood_impacts.shp"
    known = r"known\flooded_buildings.shp"
    buildings = r"input\buildings.shp"
    flooded_output = r"output\flooded_buildings.shp"
    with utils.WorkSpace(ws), utils.OverwriteState(True):
        flooded_buildings = tidegates._impact_to_buildings(
            floods_path=floods,
            ID_column="GeoID",
            buildings_path=buildings,
            buildings_output=flooded_output,
        )

    nt.assert_true(isinstance(flooded_buildings, arcpy.mapping.Layer))
    tgtest.assert_shapefiles_are_close(
        resource_filename("tidegates.testing.output", "flooded_buildings.shp"),
        resource_filename("tidegates.testing.known", "flooded_buildings.shp")
    )

    utils.cleanup_temp_results(flooded_output)
