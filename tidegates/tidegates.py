""" Top-level functions for python-tidegates.

This contains main functions to evaluate the extent of floodinga and
damage due to floods.

(c) Geosyntec Consultants, 2015.

Released under the BSD 3-clause license (see LICENSE file for more info)

Written by Paul Hobson (phobson@geosyntec.com)

"""


import os
import sys
import glob
import datetime

import numpy

import arcpy

from . import utils

__all__ = ["flood_area", "assess_impact"]


METERS_PER_FOOT = 0.3048


def flood_area(dem, zones, ID_column, elevation_feet,
               filename=None, cleanup=True, **verbose_options):
    """ Mask out portions of a a tidegates area of influence below
    a certain elevation.

    Parameters
    ----------
    dem : str or arcpy.Raster
        The (filepath to the ) Digital Elevation Model of the area.
    zones : str or arcpy.mapping.Layer
        The (filepath to the) zones that will be flooded. If a string,
        a Layer will be created.
    ID_column : str
        Name of the column in the ``zones`` layer that associates
        each geomstry with a tidegate.
    elevation_feet: float
        The theoritical flood elevation (in ft MSL) that will be
        analyzed.
    filename : str, optional
        Filename to which the flooded zone will be saved.
    cleanup : bool (default = True)
        When True, temporary results are removed from disk.

    Other Parameters
    ----------------
    verbose : bool (default = False)
        Toggles the printing of messages communication the progress
        of the processing.
    asMessage : bool (default = False)
        When True, progress messages are passed through
        ``arcpy.AddMessage``. Otherwise, the msg is simply printed to
        stdin.

    Returns
    -------
    flood_zones : arcpy.mapping.Layer
        arcpy Layer of the zones showing the extent flooded behind
        each tidegate.

    See also
    --------
    assess_impact

    """

    # convert the elevation to meters to match the DEM
    elevation_meters = elevation_feet * METERS_PER_FOOT

    if filename is None: # pragma: no cover
        datefmt = '%Y%m%d_%H%M'
        datestring = datetime.datetime.now().strftime(datefmt)
        temp_filename = "_temp_FloodedZones_" + datestring
    else:
        temp_filename = utils.create_temp_filename(filename)

    utils._status('WorkSpace set to {}'.format(arcpy.env.workspace), **verbose_options)

    # load the raw DEM (topo data)
    raw_topo = utils.load_data(
        datapath=dem,
        datatype="raster",
        msg='Loading DEM {}'.format(dem),
        **verbose_options
    )

    # load the zones of influence, converting to a raster
    _p2r_outfile = os.path.join(arcpy.env.workspace, "_temp_pgon_as_rstr.tif")
    zones_r = utils.polygons_to_raster(
        polygons=zones,
        ID_column=ID_column,
        cellsize=raw_topo.meanCellWidth,
        outfile=_p2r_outfile,
        msg='Processing {} polygons'.format(zones),
        **verbose_options
    )

    # clip the DEM to the zones raster
    _cd2z_outfile = os.path.join(arcpy.env.workspace, "_temp_clipped2zones.tif")
    topo_r = utils.clip_dem_to_zones(
        dem=raw_topo,
        zones=zones_r,
        outfile=_cd2z_outfile,
        msg='Clipping DEM to extent of {}'.format(zones),
        **verbose_options
    )

    # convert the clipped DEM and zones to numpy arrays
    zones_a, topo_a = utils.rasters_to_arrays(
        zones_r,
        topo_r,
        msg='Converting rasters to arrays',
        **verbose_options
    )

    # compute floods of zoned areas of topo
    flooded_a = utils.flood_zones(
        zones_array=zones_a,
        topo_array=topo_a,
        elevation=elevation_meters,
        msg='Flooding areas up to {} ft'.format(elevation_feet),
        **verbose_options
    )

    # convert flooded zone array back into a Raster
    _fr_outfile = os.path.join(arcpy.env.workspace, '_temp_floods_raster.tif')
    flooded_r = utils.array_to_raster(
        array=flooded_a,
        template=zones_r,
        outfile=_fr_outfile,
        msg='Converting flooded array to a raster dataset',
        **verbose_options
    )

    # convert raster into polygons
    temp_polygons = utils.raster_to_polygons(
        flooded_r,
        temp_filename,
        newfield=ID_column,
        msg='Converting raster of floods to polygons',
        **verbose_options
    )

    # dissolve (merge) broken polygons for each tidegate
    flood_zones = utils.aggregate_polygons(
        polygons=temp_polygons,
        ID_field=ID_column,
        filename=filename,
        msg="Dissolving polygons",
        **verbose_options
    )

    if cleanup:
        _temp_files = []
        utils.cleanup_temp_results(
            temp_polygons.dataSource,
            _fr_outfile,
            _cd2z_outfile,
            _p2r_outfile,
            msg="Removing intermediate files",
            **verbose_options
        )

    return flood_zones


def assess_impact(floods_path, ID_column, cleanup=False,
                  wetlands_path=None, wetlands_output=None,
                  buildings_path=None, buildings_output=None,
                  **verbose_options):
    """ Assess the extent of damage due to flooding in wetlands and
    buildings.

    Parameters
    ----------
    floods_path : str or arcpy.mapping.Layer
        The (filepath to the) layer of the extent of flooding. Ideally,
        this layer should be generated with ``flood_area``.
    ID_column : str
        Name of the column in the ``floods_path`` layer that associates
        each geomstry with a tidegate.
    wetlands_path, buildings_path : str
        Paths to layers containing wetlands and building footprints.
    wetlands_output, buildings_output : str
        Path to where the final output of the assessed damage to the
        wetlands and buildings should be saved.
    cleanup : bool (default = True)
        When True, temporary results are removed from disk.

    Other Parameters
    ----------------
    verbose : bool (default = False)
        Toggles the printing of messages communication the progress
        of the processing.
    asMessage : bool (default = False)
        When True, progress messages are passed through
        ``arcpy.AddMessage``. Otherwise, the msg is simply printed to
        stdin.

    Returns
    -------
    flooded_areas : arcpy.mapping.Layer
    flooded_wetlands : arcpy.mapping.Layer
    flooded_buildings : arcpy.mapping.Layer

    See also
    --------
    flood_area

    """

    # add total area_column and populate
    utils.add_field_with_value(floods_path, 'totalarea', field_type='DOUBLE', overwrite=True)
    utils.populate_field(
        floods_path,
        lambda row: row[0],
        'totalarea',
        'SHAPE@AREA',
    )

    if wetlands_path is not None:
        flooded_wetlands = _impact_to_wetlands(
            floods_path=floods_path,
            ID_column=ID_column,
            wetlands_path=wetlands_path,
            wetlands_output=wetlands_output,
            msg='Assessing impact to wetlands',
            **verbose_options
        )
        if cleanup:
            utils.cleanup_temp_results(flooded_wetlands)
    else:
        flooded_wetlands = None


    if buildings_path is not None:
        flooded_buildings = _impact_to_buildings(
            floods_path=floods_path,
            ID_column=ID_column,
            buildings_path=buildings_path,
            buildings_output=buildings_output,
            msg='Assessing impact to Buildings',
            **verbose_options
        )
        if cleanup:
            utils.cleanup_temp_results(flooded_buildings)
    else:
        flooded_buildings = None

    return utils.load_data(floods_path, "layer"), flooded_wetlands, flooded_buildings


@utils.update_status()
def _impact_to_wetlands(floods_path, ID_column, wetlands_path,
                        wetlands_output=None, cleanup=False,
                        **verbose_options):
    if wetlands_output is None:
        wetlands_output = 'flooded_wetlands'

    # intersect wetlands with the floods
    temp_flooded_wetlands = utils.intersect_polygon_layers(
        utils.create_temp_filename(wetlands_output),
        utils.load_data(floods_path, 'layer'),
        utils.load_data(wetlands_path, 'layer'),
        **verbose_options
    )

    # aggregate the wetlands based on the flood zone
    flooded_wetlands = utils.aggregate_polygons(
        temp_flooded_wetlands,
        ID_column,
        wetlands_output
    )

    # get area of flooded wetlands
    wetland_areas = utils.groupby_and_aggregate(
        input_path=wetlands_output,
        groupfield=ID_column,
        valuefield='SHAPE@AREA',
        aggfxn=lambda group: sum([row[1] for row in group])
    )
    # add a wetlands area field and populate
    utils.add_field_with_value(floods_path, 'wetlands', field_type='DOUBLE', overwrite=True)
    utils.populate_field(
        floods_path,
        lambda row: wetland_areas.get(row[0], -999),
        'wetlands',
        ID_column,
    )

    if cleanup:
        utils.cleanup_temp_results(temp_flooded_wetlands    )

    return flooded_wetlands


@utils.update_status()
def _impact_to_buildings(floods_path, ID_column, buildings_path,
                         buildings_output=None, **verbose_options):

    if buildings_output is None:
        buildings_output = utils.create_temp_filename('flooded_buildings')


    # intersect the buildings with the floods
    flooded_buildings = utils.intersect_polygon_layers(
        buildings_output,
        utils.load_data(floods_path, 'layer'),
        utils.load_data(buildings_path, 'layer'),
        msg='Assessing impact to buildings',
        **verbose_options
    )

    # count the number of flooding buildings in each flood zone
    building_counts = utils.groupby_and_aggregate(
        input_path=buildings_output,
        groupfield=ID_column,
        valuefield='STRUCT_ID'
    )

    # add a building count column and populate
    utils.add_field_with_value(floods_path, 'buildings', field_type='LONG', overwrite=True)
    utils.populate_field(
        floods_path,
        lambda row: building_counts.get(row[0], -1),
        'buildings',
        ID_column,
    )

    return flooded_buildings
