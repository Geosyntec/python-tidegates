import os
from pkg_resources import resource_filename

import nose.tools as nt
import numpy.testing as nptest
import tidegates.testing as tgtest
import arcpy

from tidegates import tidegates, utils


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
