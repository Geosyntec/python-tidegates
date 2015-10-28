import os
import sys
import glob
import datetime

import numpy

import arcpy


def progress_print(msg, verbose=False, asMessage=False):
    if verbose:
        if asMessage:
            arcpy.AddMessage(msg)
        else:
            print(msg)


class EasyMapDoc(object):
    def __init__(self, *args, **kwargs):
        try:
            self.mapdoc = arcpy.mapping.MapDocument(*args, **kwargs)
        except RuntimeError:
            self.mapdoc = None

    @property
    def layers(self):
        return arcpy.mapping.ListLayers(self.mapdoc)

    @property
    def dataframes(self):
        return arcpy.mapping.ListDataFrames(self.mapdoc)

    def findLayerByName(self, name):
        for lyr in self.layers:
            if not lyr.isGroupLayer and lyr.name == name:
                return lyr

    def add_layer(self, layer, df=None, position='top'):
        # if no dataframe is provided, select the first
        if df is None:
            df = self.dataframes[0]

        # check that the position is valid
        valid_positions = ['auto_arrange', 'bottom', 'top']
        if position.lower() not in valid_positions:
            raise ValueError('Position: %s is not in %s' % (position.lower, valid_positions))

        # layer can be a path to a file. if so, convert to a Layer object
        if isinstance(layer, basestring):
            layer = arcpy.mapping.Layer(layer)
        elif not isinstance(layer, arcpy.mapping.Layer):
            raise ValueError("``layer`` be an arcpy Layer or a path to a file")

        # add the layer to the map
        arcpy.mapping.AddLayer(df, layer, position.upper())

        # return the layer
        return layer


class Extension(object):
    """ Context manager to facilitate the use of ArcGIS extensions

    Inside the context manager, the extension will be checked out. Once
    the interpreter leaves the code block by any means (e.g., sucessful
    execution, raised exception) the extension will be checked back in.

    Example
    -------
    >>> import tidegates, arcpy
    >>> with tidegates.utils.Extension("spatial"):
    ...     arcpy.sa.Hillshade("C:/data/dem.tif")

    """


    def __init__(self, name):
        self.name = name

    def __enter__(self):
        if arcpy.CheckExtension(self.name) == "Available":
            status = arcpy.CheckOutExtension(self.name)
            return status
        else:
            raise RuntimeError("%s license isn't available" % self.name)

    def __exit__(self, *args):
        arcpy.CheckOutExtension(self.name)


class OverwriteState(object):
    """ Context manager to temporarily set the ``overwriteOutput``
    environment variable.

    Inside the context manager, the ``arcpy.env.overwriteOutput`` will
    be set to the given value. Once the interpreter leaves the code
    block by any means (e.g., sucessful execution, raised exception),
    ``arcpy.env.overwriteOutput`` will reset to its original value.

    Example
    -------
    >>> import tidegates
    >>> with tidegates.utils.OverwriteState(False):
    ...     # some operation that should fail if output already exists

    """

    def __init__(self, overwrite):
        self.orig_state = arcpy.env.overwriteOutput
        self.new_state = bool(overwrite)

    def __enter__(self, *args, **kwargs):
        arcpy.env.overwriteOutput = self.new_state

    def __exit__(self, *args, **kwargs):
        arcpy.env.overwriteOutput = self.orig_state


class WorkSpace(object):
    """ Context manager to temporarily set the ``workspace``
    environment variable.

    Inside the context manager, the ``arcpy.env.workspace`` will
    be set to the given value. Once the interpreter leaves the code
    block by any means (e.g., sucessful execution, raised exception),
    ``arcpy.env.workspace`` will reset to its original value.

    Example
    -------
    >>> import tidegates
    >>> with tidegates.utils.OverwriteState(False):
    ...     # some operation that should fail if output already exists

    """

    def __init__(self, path):
        self.orig_workspace = arcpy.env.workspace
        self.new_workspace = path

    def __enter__(self, *args, **kwargs):
        arcpy.env.workspace = self.new_workspace

    def __exit__(self, *args, **kwargs):
        arcpy.env.workspace = self.orig_workspace


def result_to_raster(result):
    """ Gets the actual raster from an arcpy.Result object """
    return arcpy.Raster(result.getOutput(0))


def result_to_layer(result):
    """ Gets the actual layer from an arcpy.Result object """
    return arcpy.mapping.Layer(result.getOutput(0))


def rasters_to_arrays(*rasters, **kwargs):
    """ Converts an arbitrary number of rasters to numpy arrays"""
    verbose = kwargs.pop("verbose", False)
    asMessage = kwargs.pop("asMessage", False)
    squeeze = kwargs.pop("squeeze", False)

    arrays = []
    for n, r in enumerate(rasters):
        msg = 'Processing raster {} of {}: {}'.format(n, len(rasters), r)
        progress_print(msg, verbose=verbose, asMessage=asMessage)
        arrays.append(arcpy.RasterToNumPyArray(r, nodata_to_value=-999))

    if squeeze and len(arrays) == 1:
        arrays = arrays[0]

    return arrays


def array_to_raster(array, template):
    """ Create an arcpy.Raster from a numpy.ndarray based on a template.

    Parameters
    ----------
    array : numpy.ndarray
        The array of values to be coverted to a raster.
    template : arcpy.Raster
        The raster whose, extent, position, and cell size will be
        applied to ``array``.

    Returns
    -------
    newraster : arcpy.Raster

    """

    newraster = arcpy.NumPyArrayToRaster(
        in_array=array,
        lower_left_corner=template.extent.lowerLeft,
        x_cell_size=template.meanCellWidth,
        y_cell_size=template.meanCellHeight,
        value_to_nodata=0
    )

    return newraster


def load_data(datapath, datatype, greedyRasters=True):
    """ Prepare a DEM or other raster for masking floods

    Parameters
    ----------
    datapath : str, arcpy.Raster, or arcpy.mapping.Layer
        The (filepath to the) data you want to load.
    datatype : str
        The type of data you are trying to load. Must be either
        "shape" (for polygons) or "raster" (for rasters).
    greedyRasters : bool (default = True)
        Currently, arcpy lets you load raster data as a "Raster" or as a
        "Layer". When ``greedyRasters`` is True, rasters loaded as type
        "Layer" will be forced to type "Raster".

    Returns
    -------
    data : arcpy.Raster or arcpy.mapping.Layer
        The data loaded as an arcpy type.

    """

    dtype_lookup = {
        'raster': arcpy.Raster,
        'grid': arcpy.Raster,
        'shape': arcpy.mapping.Layer,
        'layer': arcpy.mapping.Layer,
    }

    try:
        objtype = dtype_lookup[datatype.lower()]
    except KeyError:
        raise ValueError("Datatype {} not supported. Must be raster or layer".format(datatype))

    # if the input is already a Raster or Layer, just return it
    if isinstance(datapath, objtype):
        data = datapath
    # otherwise, load it as the datatype
    else:
        try:
            data = objtype(datapath)
        except:
            raise ValueError("could not load {} as a {}".format(datapath, objtype))

    if greedyRasters and isinstance(data, arcpy.mapping.Layer) and data.isRasterLayer:
        data = arcpy.Raster(datapath)

    return data


def process_polygons(polygons, tidegate_column, cellsize=4):
    """ Prepare tidegates' areas of influence polygons for flooding
    by converting to a raster.

    Parameters
    ----------
    polygons : str or arcpy.mapping.Layer
        The (filepath to the) zones that will be flooded. If a string,
        a Layer will be created.
    tidegate_column : str
        Name of the column in the ``polygons`` layer that associates
        each geomstry with a tidegate.
    cellsize : int
        Desired cell dimension of the output raster. Default is 4 m.

    Returns
    -------
    zones : arcpy.Raster
        The zones of influence as a raster dataset
    result : arcpy.Result
        The weird, crpyric results object that so many (but not all)
        ESRI arcpy function return.

    """

    _zones = load_data(polygons, 'shape')

    with OverwriteState(True), Extension("spatial"):
        result = arcpy.conversion.PolygonToRaster(
            in_features=_zones,
            value_field=tidegate_column,
            cellsize=cellsize,
        )

    # result object isn't actually the raster
    # need to read in the raster as an object
    # the file path embedded in the result
    zones = result_to_raster(result)

    return zones, result


def clip_dem_to_zones(dem, zones):
    """ Limits the extent of the topographic data (``dem``) to that of
    the zones of influence  so that we can easily use array
    representations of the rasters.

    Parameters
    ----------
    dem : arcpy.Raster
        Digital elevation model of the area of interest.
    zones : arcpy.Raster
        The raster whose cell values represent the zones of influence
        of each tidegate.

    Returns
    -------
    dem_clipped : arcpy.Raster
        The zones of influence as a raster dataset
    result : arcpy.Result
        The weird, cryptic results object that so many (but not all)
        ESRI arcpy function return.

    """

    _dem = load_data(dem, "raster")
    _zones = load_data(zones, "raster")

    with OverwriteState(True) as state:
        result = arcpy.management.Clip(
            in_raster=_dem,
            in_template_dataset=_zones,
            out_raster="_temp_clipped",
            maintain_clipping_extent="MAINTAIN_EXTENT",
            clipping_geometry="NONE",
        )

    dem_clipped = result_to_raster(result)

    return dem_clipped, result


def flood_zones(zones_array, topo_array, elevation):
    """ Mask out non-flooded portions of rasters.

    Parameters
    ----------
    zones_array : numpy.ndarray
        Array of zone IDs from each zone of influence.
    topo_array : numpy.ndarray
        Digital elevation model (as an array) of the areas.
    elevation : float
        The flood elevation *above& which everything will be masked.

    Returns
    -------
    flooded_array : numpy.ndarray
        Array of zone IDs only where there is flooding.

    """

    # compute mask of non-zoned areas of topo
    nonzone_mask = zones_array <= 0

    invalid_mask = numpy.ma.masked_invalid(topo_array).mask
    topo_array[invalid_mask] = -999

    # mask out zoned areas above the flood elevation
    unflooded_mask = topo_array > elevation

    # apply the mask to the zone array
    final_mask = nonzone_mask | unflooded_mask
    flooded_array = zones_array.copy()
    flooded_array[final_mask] = 0

    return flooded_array
