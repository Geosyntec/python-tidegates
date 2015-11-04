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
        layer = tidegates.assess_impact(
            floods_path=floods,
            ID_column="GeoID",
            wetlands_path=wetlands,
            buildings_path=buildings,
            buildingsoutput=r"output\flooded_buildings.shp",
            wetlandsoutput=r"output\flooded_wetlands.shp",
            cleanup=True,
        )

    nt.assert_true(isinstance(layer, arcpy.mapping.Layer))
    tgtest.assert_shapefiles_are_close(
        resource_filename("tidegates.testing.output", "flood_impacts.shp"),
        resource_filename("tidegates.testing.known", "flood_impacts.shp")
    )
