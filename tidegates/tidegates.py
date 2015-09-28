import os
import sys
import glob
import datetime

import numpy

import arcpy

from . import utils

__all__ = ["flood_area", "assess_impact"]


METERS_PER_FEET = 0.3048
MHHW = 4  * METERS_PER_FEET # GUESS
SURGES = {
    'MHHW' :   4.0 * METERS_PER_FEET, # no storm surge
    '10-yr':   8.0 * METERS_PER_FEET, #  10-yr (approx)
    '25-yr':   8.5 * METERS_PER_FEET, #  25-yr (guess)
    '50-yr':   9.6 * METERS_PER_FEET, #  50-yr (approx)
    '100-yr': 10.5 * METERS_PER_FEET, # 100-yr (guess
}

def flood_area(dem, polygons, tidegate_column, sea_level_rise, storm_surge, filename=None):
    """ Mask out portions of a a tidegates area of influence below
    a certain elevation.

    Parameters
    ----------
    dem : str or arcpy.Raster
        The (filepath to the ) Digital Elevation Model of the area.
    polygons : str or arcpy.mapping.Layer
        The (filepath to the) zones that will be flooded. If a string,
        a Layer will be created.
    tidegate_column : str
        Name of the column in the ``polygons`` layer that associates
        each geomstry with a tidegate.
    sea_level_rise : float
        The amount of sea level rise to be evaluated (in feet).
    storm_surge : string
        The return period of the storm surge event to be analyzed.
        Valid values are "MHHW", "10-yr", "25-yr", "100-yr"
    filename : str, optional
        Filename to which the flooded zone will be saved.

    Returns
    -------
    flood_polygons : arcpy.mapping.Layer
        arcpy Layer of the polygons showing the extent flooded behind
        each tidegate.

    """

    # add up the sea level rise and storm sturge to a single elevation
    try:
        elevation = SURGES[storm_surge] + sea_level_rise
    except KeyError:
        msg = '{} is not a valid surge event. Valid values are {}'
        raise ValueError(msg.format(storm_surge, SURGES.keys()))

    # load the raw (full extent) DEM (topo data)
    raw_topo = utils.load_data(dem, "raster")

    # load the zones of influence, converting to a raster
    zones_r, zone_res = utils.process_polygons(polygons, tidegate_column)

    # clip the DEM to the zones raster
    topo_r, topo_res = utils.clip_dem_to_zones(raw_topo, zones_r)

    # convert the clipped DEM and zones to numpy arrays
    arcpy.AddMessage(zones_r)
    zones_a, topo_a = utils.rasters_to_arrays(zones_r, topo_r)

    # compute mask of non-zoned areas of topo
    nonzone_mask = zones_a <= 0

    invalid_mask = numpy.ma.masked_invalid(topo_a).mask
    topo_a[invalid_mask] = -999

    # mask out zoned areas above the flood elevation
    unflooded_mask = topo_a > elevation

    # apply the mask to the zone array
    final_mask = nonzone_mask | unflooded_mask
    flooded_a = zones_a.copy()
    flooded_a[final_mask] = 0

    # convert masked zone array back into a Raster
    flooded_r = utils.array_to_raster(array=flooded_a, template=zones_r)

    if filename is None:
        datefmt = '%Y%m%d_%H%M'
        datestring = datetime.datetime.now().strftime(datefmt)
        temp_filename = "_temp_FloodedZones_" + datestring
    else:
        temp_filename = '_temp_' + filename

    # convert raster into polygons
    temp_result = arcpy.conversion.RasterToPolygon(
        in_raster=flooded_r,
        out_polygon_features=temp_filename
    )

    # dissolve (merge) broken polygons for each tidegate
    flood_polygons = arcpy.management.Dissolve(
        in_features=utils.result_to_layer(temp_result),
        out_feature_class=filename,
        dissolve_field="gridcode",
        statistics_fields='#'
    )

    return flood_polygons


def assess_impact(flood_layer, input_gdb, overwrite=False):
    outputlayers = []
    assetnames = ["Landuse", "SaltMarsh", "Wetlands"]


    with utils.OverwriteState(overwrite):
        with utils.WorkSpace(input_gdb):
            print(arcpy.env.workspace)
            input_layer = utils.load_data(flood_layer, "shape")
            # loop through the selected assets
            for asset in assetnames:
                # create the asset layer object
                print('load asset layer {}'.format(asset))
                assetlayer = utils.load_data(asset, "shape")

                # intersect the flooding with the asset
                outputpath = '{}_{}'.format(flood_layer, asset)
                print("save intersection to {}".format(outputpath))
                result = arcpy.analysis.Intersect([input_layer, assetlayer], outputpath)

                # append instersetected layer to the output list
                print("save results")
                outputlayers.append(utils.result_to_layer(result))

    return outputlayers


def _assess_impact(inputspace, outputspace, SLR, surge, overwrite, assetnames):
    print(assetnames)
    INPUT_FLOOD_LAYER = "FloodScenarios"
    outputlayers = []

    # flood layer object for the flooding and query for our scenario
    floodlayer = arcpy.mapping.Layer(os.path.join(inputspace, INPUT_FLOOD_LAYER))

    ## create the query string
    qry = '"SLR" = %d AND "surge" = \'%s\'' % (int(SLR), surge)

    ## apply the query to the layer
    floodlayer.definitionQuery = qry

    # add the layer to list of layer that will be output
    outputlayers.append(floodlayer)

    with utils.OverwriteState(overwrite) as state:
        # loop through the selected assets
        for asset in assetnames.split(';'):

            # create the asset layer object
            assetlayer = arcpy.mapping.Layer(os.path.join(inputspace, asset))
            #assetlayer = arcpy.mapping.Layer(asset)

            # intersect the flooding with the  asset
            outputpath = os.path.join(outputspace, "Test_Flood_%s_%d_%s" % (asset, int(SLR), surge))
            result = arcpy.analysis.Intersect([floodlayer, assetlayer], outputpath)

            # create a layer object of the intersected areas
            intersectedlayer = arcpy.mapping.Layer(result.getOutput(0))

            # append instersetected layer to the output list
            outputlayers.append(intersectedlayer)

    return outputlayers


# if __name__ == '__main__':
#     # input from dialogue
#     outputlayers = flood_area(*sys.argv[2:])
#     mapdoc = EasyMapDoc("CURRENT")
#     for lyr in outputlayers:
#         mapdoc.add_layer(lyr)
