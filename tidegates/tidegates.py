import os
import sys
import glob
import datetime

import numpy

import arcpy

from . import utils

__all__ = ["flood_area", "assess_impact", "SURGES"]


METERS_PER_FEET = 0.3048
MHHW = 4  * METERS_PER_FEET # GUESS
SURGES = {
    'MHHW' :   4.0 * METERS_PER_FEET, # no storm surge
    '10-yr':   8.0 * METERS_PER_FEET, #  10-yr (approx)
    '25-yr':   8.5 * METERS_PER_FEET, #  25-yr (guess)
    '50-yr':   9.6 * METERS_PER_FEET, #  50-yr (approx)
    '100-yr': 10.5 * METERS_PER_FEET, # 100-yr (guess
}


def progress_print(verbose, msg):
    if verbose:
        print(msg)


def flood_area(dem, polygons, tidegate_column, sea_level_rise, storm_surge,
               filename=None, workspace=None, verbose=False):
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

    if filename is None:
        datefmt = '%Y%m%d_%H%M'
        datestring = datetime.datetime.now().strftime(datefmt)
        temp_filename = "_temp_FloodedZones_" + datestring
    else:
        temp_filename = '_temp_' + filename

    progress_print(verbose, '1/9 {}'.format(arcpy.env.workspace))
    # load the raw (full extent) DEM (topo data)
    raw_topo = utils.load_data(dem, "raster")
    progress_print(verbose, '2/9 {} raster loaded'.format(dem))

    # load the zones of influence, converting to a raster
    zones_r, zone_res = utils.process_polygons(polygons, tidegate_column)
    progress_print(verbose, '3/9 {} polygon processed'.format(polygons))

    # clip the DEM to the zones raster
    topo_r, topo_res = utils.clip_dem_to_zones(raw_topo, zones_r)
    progress_print(verbose, '4/9 topo clipped')

    # convert the clipped DEM and zones to numpy arrays
    arcpy.AddMessage(zones_r)
    zones_a, topo_a = utils.rasters_to_arrays(zones_r, topo_r)
    progress_print(verbose, '5/9 rasters to arrays')

    # compute mask of non-zoned areas of topo
    flooded_a = utils.mask_array_with_flood(zones_a, topo_a, elevation)
    progress_print(verbose, '6/9 mask things')

    # convert masked zone array back into a Raster
    flooded_r = utils.array_to_raster(array=flooded_a, template=zones_r)
    flooded_r.save('tempraster')
    progress_print(verbose, '7/9 coverted back to raster and saved')

    # convert raster into polygons
    progress_print(verbose, '8/9 convert to polygon in {}'.format(arcpy.env.workspace))
    temp_result = arcpy.conversion.RasterToPolygon(
        in_raster=flooded_r,
        out_polygon_features=temp_filename,
        simplify="SIMPLIFY",
        raster_field="Value"
    )

    # dissolve (merge) broken polygons for each tidegate
    flood_polygons = arcpy.management.Dissolve(
        in_features=utils.result_to_layer(temp_result),
        out_feature_class=filename,
        dissolve_field="gridcode",
        statistics_fields='#'
    )
    progress_print(verbose, '9/9 dissolve')

    return flood_polygons


def assess_impact(flood_layer, input_gdb, overwrite=False, verbose=False):
    outputlayers = []
    assetnames = ["Landuse", "SaltMarsh", "Wetlands"]


    with utils.OverwriteState(overwrite):
        with utils.WorkSpace(input_gdb):
            progress_print(verbose, arcpy.env.workspace)
            input_layer = utils.load_data(flood_layer, "shape")
            # loop through the selected assets
            for asset in assetnames:
                # create the asset layer object
                progress_print(verbose, 'load asset layer {}'.format(asset))
                assetlayer = utils.load_data(asset, "shape")

                # intersect the flooding with the asset
                outputpath = '{}_{}'.format(flood_layer, asset)
                progress_print(verbose, "save intersection to {}".format(outputpath))
                result = arcpy.analysis.Intersect([input_layer, assetlayer], outputpath)

                # append instersetected layer to the output list
                progress_print(verbose, "save results")
                outputlayers.append(utils.result_to_layer(result))

    return outputlayers


def _assess_impact(inputspace, outputspace, SLR, surge, overwrite, assetnames):
    progress_print(verbose, assetnames)
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
