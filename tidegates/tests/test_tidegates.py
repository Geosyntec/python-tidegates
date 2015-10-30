from pkg_resources import resource_filename

import nose.tools as nt
import numpy.testing as nptest
import tidegates.testing as tgtest
import arcpy

from tidegates import tidegates, utils


def test_flood_area():
    ws = resource_filename("tidegates", "testing")
    with utils.WorkSpace(ws), utils.OverwriteState(True):
        filename = "test_flood_area_output.shp"
        result = tidegates.flood_area(
            dem='test_dem.tif',
            polygons='test_zones.shp',
            ID_column="GeoID",
            elevation_feet=7.8,
            filename=filename,
            verbose=False
        )
        result.saveToFile(filename)

    nt.assert_true(isinstance(result, arcpy.Result))
    tgtest.assert_shapefiles_are_close(
        resource_filename("tidegates.testing", "known_flood_area_output.shp"),
        resource_filename("tidegates.testing", filename)
    )

    utils.cleanup_temp_results(result)

