""" Basic utility functions for python-tidegates.

This contains basic file I/O, coversion, and spatial analysis functions
to support the python-tidegates library. In most cases, these functions
are simply wrappers around their ``arcpy`` counter parts. This was done
so that in the future, these functions could be replaces with calls to
a different geoprocessing library and eventually ween the code base off
of its ``arcpy`` dependency.

(c) Geosyntec Consultants, 2015.

Released under the BSD 3-clause license (see LICENSE file for more info)

Written by Paul Hobson (phobson@geosyntec.com)

"""


import os
import datetime
from functools import wraps
import itertools

import numpy

import arcpy


class EasyMapDoc(object):
    """ The object-oriented map class Esri should have made.

    Create this the same you would make any other
    `arcpy.mapping.MapDocument`_. But now, you can directly list and
    add layers and dataframes. See the two examples below.

    Has ``layers`` and ``dataframes`` attributes that return all of the
    `arcpy.mapping.Layer`_ and `arcpy.mapping.DataFrame`_ objects in the
    map, respectively.

    .. _arcpy.mapping.MapDocument: http://resources.arcgis.com/EN/HELP/MAIN/10.2/index.html#/MapDocument/00s30000000n000000/
    .. _arcpy.mapping.DataFrame: http://resources.arcgis.com/EN/HELP/MAIN/10.2/index.html#/DataFrame/00s300000003000000/
    .. _arcpy.mapping.Layer: http://resources.arcgis.com/EN/HELP/MAIN/10.2/index.html#/Layer/00s300000008000000/

    Attributes
    ----------
    mapdoc : arcpy.mapping.MapDocument
        The underlying arcpy MapDocument that serves as the basis for
        this class.

    Examples
    --------
    >>> # Adding a layer with the Esri version:
    >>> import arpcy
    >>> md = arcpy.mapping.MapDocument('CURRENT')
    >>> df = arcpy.mapping.ListDataFrames(md)
    >>> arcpy.mapping.AddLayer(df, myLayer, 'TOP')

    >>> # And now with an ``EasyMapDoc``:
    >>> from tidegates import utils
    >>> ezmd = utils.EasyMapDoc('CURRENT')
    >>> ezmd.add_layer(myLayer)

    """

    def __init__(self, *args, **kwargs):
        try:
            self.mapdoc = arcpy.mapping.MapDocument(*args, **kwargs)
        except RuntimeError:
            self.mapdoc = None

    @property
    def layers(self):
        """
        All of the layers in the map.
        """
        return arcpy.mapping.ListLayers(self.mapdoc)

    @property
    def dataframes(self):
        """
        All of the dataframes in the map.
        """
        return arcpy.mapping.ListDataFrames(self.mapdoc)

    def findLayerByName(self, name):
        """ Finds a `layer`_ in the map by searching for an exact match
        of its name.

        .. _layer: http://resources.arcgis.com/EN/HELP/MAIN/10.2/index.html#/Layer/00s300000008000000/

        Parameters
        ----------
        name : str
            The name of the layer you want to find.

        Returns
        -------
        lyr : arcpy.mapping.Layer
            The map layer or None if no match is found.

        .. warning:: Group Layers are not returned.

        Examples
        --------
        >>> from tidegates import utils
        >>> ezmd = utils.EasyMapDoc('CURRENT')
        >>> wetlands = ezmd.findLayerByName("wetlands")
        >>> if wetlands is not None:
        ...     # do something with `wetlands`

        """

        for lyr in self.layers:
            if not lyr.isGroupLayer and lyr.name == name:
                return lyr

    def add_layer(self, layer, df=None, position='top'):
        """ Simply adds a `layer`_ to a map.

        .. _layer: http://resources.arcgis.com/EN/HELP/MAIN/10.2/index.html#/Layer/00s300000008000000/

        Parameters
        ----------
        layer : str or arcpy.mapping.Layer
            The dataset to be added to the map.
        df : arcpy.mapping.DataFrame, optional
            The specific dataframe to which the layer will be added. If
            not provided, the data will be added to the first dataframe
            in the map.
        position : str, optional ('TOP')
            The positional within `df` where the data will be added.
            Valid options are: 'auto_arrange', 'bottom', and 'top'.

        Returns
        -------
        layer : arcpy.mapping.Layer
            The sucessfully added layer.

        Examples
        --------
        >>> from tidegates import utils
        >>> ezmd = utils.EasyMapDoc('CURRENT')
        >>> ezmd.add_layer(myLayer)

        """

        # if no dataframe is provided, select the first
        if df is None:
            df = self.dataframes[0]

        # check that the position is valid
        valid_positions = ['auto_arrange', 'bottom', 'top']
        if position.lower() not in valid_positions:
            raise ValueError('Position: %s is not in %s' % (position.lower, valid_positions))

        # layer can be a path to a file. if so, convert to a Layer object
        layer = load_data(layer, 'layer')

        # add the layer to the map
        arcpy.mapping.AddLayer(df, layer, position.upper())

        # return the layer
        return layer


class Extension(object):
    """ Context manager to facilitate the use of ArcGIS extensions

    Inside the context manager, the extension will be checked out. Once
    the interpreter leaves the code block by any means (e.g., sucessful
    execution, raised exception) the extension will be checked back in.

    Examples
    --------
    >>> import tidegates, arcpy
    >>> with tidegates.utils.Extension("spatial"):
    ...     arcpy.sa.Hillshade("C:/data/dem.tif")

    """


    def __init__(self, name):
        self.name = name

    def __enter__(self):
        if arcpy.CheckExtension(self.name) == u"Available":
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

    Examples
    --------
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

    Inside the context manager, the `arcpy.env.workspace`_ will
    be set to the given value. Once the interpreter leaves the code
    block by any means (e.g., sucessful execution, raised exception),
    `arcpy.env.workspace`_ will reset to its original value.

    .. _arcpy.env.workspace: http://resources.arcgis.com/EN/HELP/MAIN/10.2/index.html#/Current_Workspace/001w00000002000000/

    Parameters
    ----------
    path : str
        Path to the directory that will be set as the current workspace.

    Examples
    --------
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


def _status(msg, verbose=False, asMessage=False, addTab=False): # pragma: no cover
    if verbose:
        if addTab:
            msg = '\t' + msg
        if asMessage:
            arcpy.AddMessage(msg)
        else:
            print(msg)


def update_status(): # pragma: no cover
    """ Decorator to allow a function to take a additional keyword
    arguments related to printing status messages to stdin or as arcpy
    messages.

    """

    def decorate(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            msg = kwargs.pop("msg", None)
            verbose = kwargs.pop("verbose", False)
            asMessage = kwargs.pop("asMessage", False)
            addTab = kwargs.pop("addTab", False)
            _status(msg, verbose=verbose, asMessage=asMessage, addTab=addTab)

            return func(*args, **kwargs)
        return wrapper
    return decorate


def create_temp_filename(filepath, prefix='_temp_'):
    """ Helper function to create temporary filenames before to be saved
    before the final output has been generated.

    Parameters
    ----------
    filepath : str
        The file path/name of what the final output will eventually be.
    prefix : str, optional ('_temp_')
        The prefix that will be applied to ``filepath``.

    Returns
    -------
    str

    Examples
    --------
    >>> create_temp_filename('path/to/flooded_wetlands.shp')
    path/to/_temp_flooded_wetlands.shp

    """

    file_with_ext = os.path.basename(filepath)
    folder = os.path.dirname(filepath)
    return os.path.join(folder, prefix + file_with_ext)


def _check_fields(table, *fieldnames, **kwargs):
    """
    Checks that field are (or are not) in a table. The check fails, a
    ``ValueError`` is raised. Relies on `arcpy.ListFields`_.

    .. _arcpy.ListFields: http://resources.arcgis.com/EN/HELP/MAIN/10.2/index.html#/ListFields/03q30000001t000000/

    Parameters
    ----------
    table : arcpy.mapping.Layer or similar
        Any table-like that we can pass to `arcpy.ListFields`.
    *fieldnames : str arguments
        optional string arguments that whose existance in `table` will
        be checked.
    should_exist : bool, optional (False)
        Whether we're testing for for absense (False) or existance
        (True) of the provided field names.

    Returns
    -------
    None

    """

    should_exist = kwargs.pop('should_exist', False)

    existing_fields = [field.name for field in arcpy.ListFields(table)]
    bad_names = []
    for name in fieldnames:
        exists = name in existing_fields
        if should_exist != exists and name != 'SHAPE@AREA':
            bad_names.append(name)

    if not should_exist:
        qual = 'already'
    else:
        qual = 'not'

    if len(bad_names) > 0:
        raise ValueError('fields {} are {} in {}'.format(bad_names, qual, table))


@update_status() # raster
def result_to_raster(result):
    """ Gets the actual `arcpy.Raster`_ from an `arcpy.Result`_ object.

    .. _arcpy.Raster: http://resources.arcgis.com/EN/HELP/MAIN/10.2/index.html#/Raster/018z00000051000000/
    .. _arcpy.Result: http://resources.arcgis.com/EN/HELP/MAIN/10.2/index.html#/Result/018z00000046000000/

    Parameters
    ----------
    result : arcpy.Result
        The `Result` object returned from some other geoprocessing
        function.

    Returns
    -------
    arcpy.Raster

    See also
    --------
    result_to_layer

    """
    return arcpy.Raster(result.getOutput(0))


@update_status() # layer
def result_to_layer(result):
    """ Gets the actual `arcpy.mapping.Layer`_ from an `arcpy.Result`_
    object.

    .. _arcpy.mapping.Layer: http://resources.arcgis.com/EN/HELP/MAIN/10.2/index.html#/Layer/00s300000008000000/
    .. _arcpy.Result: http://resources.arcgis.com/EN/HELP/MAIN/10.2/index.html#/Result/018z00000046000000/

    Parameters
    ----------
    result : arcpy.Result
        The `Result` object returned from some other geoprocessing
        function.

    Returns
    -------
    arcpy.mapping.Layer

    See also
    --------
    result_to_raster

    """

    return arcpy.mapping.Layer(result.getOutput(0))


@update_status() # list of arrays
def rasters_to_arrays(*rasters, **kwargs):
    """ Converts an arbitrary number of `rasters`_ to `numpy arrays`_.
    Relies on `arcpy.

    .. _rasters: http://resources.arcgis.com/EN/HELP/MAIN/10.2/index.html#/Raster/018z00000051000000/
    .. _numpy arrays: http://docs.scipy.org/doc/numpy/reference/generated/numpy.array.html
    .. _arcpy.RasterToNumPyArray: http://resources.arcgis.com/EN/HELP/MAIN/10.2/index.html#/RasterToNumPyArray/03q300000029000000/

    Parameters
    ----------
    rasters : args of numpy.arrays
        Rasters that will be converted to arrays.
    squeeze : bool, optional (False)
        By default (``squeeze = False``) a list of arrays is always
        returned. However, when ``squeeze = True`` and only one raster
        is provided, the array will be **squeezed** out of the list
        and returned directly.

    Returns
    -------
    arrays : list of arrays or array.

    See also
    --------
    array_to_raster
    result_to_raster
    polygons_to_raster

    """

    squeeze = kwargs.pop("squeeze", False)

    arrays = []
    for n, r in enumerate(rasters):
        arrays.append(arcpy.RasterToNumPyArray(r, nodata_to_value=-999))

    if squeeze and len(arrays) == 1:
        arrays = arrays[0]

    return arrays


@update_status() # raster
def array_to_raster(array, template, outfile=None):
    """ Create an arcpy.Raster from a numpy.ndarray based on a template.
    This wrapper around `arcpy.NumPyArrayToRaster`_.

    .. _arcpy.NumPyArrayToRaster: http://resources.arcgis.com/en/help/main/10.2/03q3/03q30000007q000000.htm

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

    See also
    --------
    rasters_to_arrays
    polygons_to_raster

    Examples
    --------
    >>> from tidegates import utils
    >>> raster = utils.load_data('dem.tif', 'raster') # in meters
    >>> array = utils.rasters_to_arrays(raster, squeeze=True)
    >>> array = array / 0.3048 # convert elevations to feet
    >>> newraster = utils.array_to_raster(array, raster)
    >>> newraster.save('<path_to_output>')

    """

    newraster = arcpy.NumPyArrayToRaster(
        in_array=array,
        lower_left_corner=template.extent.lowerLeft,
        x_cell_size=template.meanCellWidth,
        y_cell_size=template.meanCellHeight,
        value_to_nodata=0
    )

    if outfile is not None:
        newraster.save(outfile)

    return newraster


@update_status() # raster or layer
def load_data(datapath, datatype, greedyRasters=True, **verbosity):
    """ Loads vector and raster data from filepaths.

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
    data : `arcpy.Raster`_ or `arcpy.mapping.Layer`_
        The data loaded as an arcpy object.

    .. _arcpy.Raster: http://resources.arcgis.com/EN/HELP/MAIN/10.2/index.html#/Raster/018z00000051000000/
    .. _arcpy.mapping.Layer: http://resources.arcgis.com/EN/HELP/MAIN/10.2/index.html#/Layer/00s300000008000000/

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


@update_status() # raster
def polygons_to_raster(polygons, ID_column, cellsize=4, outfile=None):
    """ Prepare tidegates' areas of influence polygons for flooding
    by converting to a raster. Relies on
    `arcpy.conversion.PolygonToRaster`_.

    .. _arcpy.conversion.PolygonToRaster: http://resources.arcgis.com/EN/HELP/MAIN/10.2/index.html#//001200000030000000

    Parameters
    ----------
    polygons : str or arcpy.mapping.Layer
        The (filepath to the) zones that will be flooded. If a string,
        a Layer will be created.
    ID_column : str
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

    Examples
    --------
    >>> zone_raster, res = utils.polygons_to_raster('ZOI.shp', 'GeoID')
    >>> zone_array = utils.rasters_to_arrays(zone_raster, squeeze=True)
    >>> # remove all zones with a GeoID less than 5
    >>> zone_array[zone_array < 5] = 0
    >>> filtered_raster = utils.array_to_raster(zone_array, zone_raster)

    See also
    --------
    raster_to_polygons
    rasters_to_arrays
    array_to_raster

    """

    _zones = load_data(polygons, 'shape')

    with OverwriteState(True), Extension("spatial"):
        result = arcpy.conversion.PolygonToRaster(
            in_features=_zones,
            value_field=ID_column,
            cellsize=cellsize,
            out_rasterdataset=outfile,
        )

    zones = result_to_raster(result)

    return zones


@update_status() # raster
def clip_dem_to_zones(dem, zones, outfile=None):
    """ Limits the extent of the topographic data (``dem``) to that of
    the zones of influence  so that we can easily use array
    representations of the rasters. Relies on `arcpy.management.Clip`_.

    .. _arcpy.management.Clip: http://resources.arcgis.com/EN/HELP/MAIN/10.2/index.html#//00170000009n000000

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
            out_raster=outfile,
            maintain_clipping_extent="MAINTAIN_EXTENT",
            clipping_geometry="NONE",
        )

    dem_clipped = result_to_raster(result)

    return dem_clipped


@update_status() # layer
def raster_to_polygons(zonal_raster, filename, newfield=None):
    """
    Converts zonal rasters to polygons layers. This is basically just
    a thing wrapper around arcpy.conversion.RasterToPolygon. The
    returned layers will have a field that corresponds to the values of
    the raster. The name of this field can be controlled with the
    ``newfield`` parameter.

    Relies on `arcpy.conversion.RasterToPolygon`_.

    .. _arcpy.conversion.RasterToPolygon: http://resources.arcgis.com/EN/HELP/MAIN/10.2/index.html#//001200000008000000


    Parameters
    ----------
    zonal_raster : arcpy.Raster
        An integer raster of reasonably small set distinct values.
    filename : str
        Path to where the polygons will be saved.
    newfield : str, optional
        By default, the field that contains the raster values is called
        "gridcode". Use this parameter to change the name of that field.

    Returns
    -------
    polygons : arcpy.mapping.Layer
        The converted polygons.

    See also
    --------
    polygons_to_raster
    add_field_with_value
    populate_field

    """

    results = arcpy.conversion.RasterToPolygon(
        in_raster=zonal_raster,
        out_polygon_features=filename,
        simplify="SIMPLIFY",
        raster_field="Value",
    )


    if newfield is not None:
        for field in arcpy.ListFields(filename):
            if field.name.lower() == 'gridcode':
                gridfield = field.name

        add_field_with_value(filename, newfield, field_type="LONG")
        populate_field(filename, lambda x: x[0], newfield, gridfield)

    polygons = result_to_layer(results)
    return polygons


@update_status() # layer
def aggregate_polygons(polygons, ID_field, filename):
    """
    Dissolves (aggregates) polygons into a single feature the unique
    values in the provided field. This is basically just a thim wrapper
    around `arcpy.management.Dissolve`_.

    .. _arcpy.management.Dissolve: http://resources.arcgis.com/en/help/main/10.2/index.html#//00170000005n000000

    Parameters
    ----------
    polygons : arcpy.mapping.Layer
        The layer of polygons to be aggregated.
    ID_field : string
        The name of the field in ``polygons`` on which the individual
        polygons will be grouped.
    filename : string
        Path to where the aggregated polygons will be saved.

    Returns
    -------
    dissolved : arcpy.mapping.Layer
        The aggregated polygons.

    Examples
    --------
    >>> from tidegates import utils
    >>> dissolved = utils.aggregate_polygons('wetlands.shp', 'GeoID',
    ...                                      'dissolved.shp')

    See also
    --------
    arcpy.management.Dissolve

    """

    results = arcpy.management.Dissolve(
        in_features=polygons,
        dissolve_field=ID_field,
        out_feature_class=filename,
        statistics_fields='#'
    )

    dissolved = result_to_layer(results)
    return dissolved


@update_status() # array
def flood_zones(zones_array, topo_array, elevation):
    """ Mask out non-flooded portions of arrays.

    Parameters
    ----------
    zones_array : numpy.array
        Array of zone IDs from each zone of influence.
    topo_array : numpy.array
        Digital elevation model (as an array) of the areas.
    elevation : float
        The flood elevation *above* which everything will be masked.

    Returns
    -------
    flooded_array : numpy.array
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


@update_status() # None
def add_field_with_value(table, field_name, field_value=None,
                         overwrite=False, **field_opts):
    """ Adds a numeric or text field to an attribute table and sets it
    to a constant value. Operates in-place and therefore does not
    return anything.

    Relies on `arcpy.management.AddField`_.

    .. _arcpy.management.AddField: http://resources.arcgis.com/en/help/main/10.2/index.html#//001700000047000000

    Parameters
    ----------
    table : Layer, table, or file path
        This is the layer/file that will have a new field created.
    field_name : string
        The name of the field to be created.
    field_value : float or string, optional
        The value of the new field. If provided, it will be used to
        infer the ``field_type`` parameter required by
        `arcpy.management.AddField` if ``field_type`` is itself not
        explicitly provided.
    overwrite : bool, optonal (False)
        If True, an existing field will be overwritting. The default
        behaviour will raise a `ValueError` if the field already exists.
    **field_opts : keyword options
        Keyword arguments that are passed directly to
        `arcpy.management.AddField`.

    Returns
    -------
    None

    Examples
    --------
    >>> # add a text field to shapefile (text fields need a length spec)
    >>> utils.add_field_with_value("mypolygons.shp", "storm_event",
                                   "100-yr", field_length=10)
    >>> # add a numeric field (doesn't require additional options)
    >>> utils.add_field_with_value("polygons.shp", "flood_level", 3.14)

    """

    # how Esri map python types to field types
    typemap = {
        int: 'LONG',
        float: 'DOUBLE',
        unicode: 'TEXT',
        str: 'TEXT',
        type(None): None
    }

    # pull the field type from the options if it was specified,
    # otherwise lookup a type based on the `type(field_value)`.
    field_type = field_opts.pop("field_type", typemap[type(field_value)])

    if not overwrite:
        _check_fields(table, field_name, should_exist=False)

    if field_value is None and field_type is None:
        raise ValueError("must provide a `field_type` if not providing a value.")

    # see http://goo.gl/66QD8c
    arcpy.management.AddField(
        in_table=table,
        field_name=field_name,
        field_type=field_type,
        **field_opts
    )

    # set the value in all rows
    if field_value is not None:
        populate_field(table, lambda row: field_value, field_name)


@update_status() # None
def cleanup_temp_results(*results):
    """ Deletes temporary results from the current workspace.

    Relies on `arcpy.management.Delete`_.

    .. _arcpy.management.Delete: http://resources.arcgis.com/en/help/main/10.2/index.html#//001700000052000000

    Parameters
    ----------
    *results : str
        Paths to the temporary results

    Returns
    -------
    None

    """
    for r in results:
        if isinstance(r, basestring):
            path = r
        elif isinstance(r, arcpy.Result):
            path = r.getOutput(0)
        elif isinstance(r, arcpy.mapping.Layer):
            path = r.dataSource
        elif isinstance(r, arcpy.Raster):
            # Esri docs are incorrect here:
            # --> http://goo.gl/67NwDj
            # path doesn't include the name
            path = os.path.join(r.path, r.name)
        else:
            raise ValueError("Input must be paths, Results, Rasters, or Layers")

        fullpath = os.path.join(os.path.abspath(arcpy.env.workspace), path)
        arcpy.management.Delete(fullpath)


@update_status() # layer
def intersect_polygon_layers(destination, *layers, **intersect_options):
    """
    Intersect polygon layers with each other. Basically a thin wrapper
    around `arcpy.analysis.Intersect`_.

    .. _arcpy.analysis.Intersect: http://resources.arcgis.com/en/help/main/10.2/index.html#//00080000000p000000

    Parameters
    ----------
    destination : str
        Filepath where the intersected output will be saved.
    *layers : str or arcpy.Mapping.Layer
        The polygon layers (or their paths) that will be intersected
        with each other.
    **intersect_options : keyword arguments
        Additional arguments that will be passed directly to
        `arcpy.analysis.Intersect`.

    Returns
    -------
    intersected : arcpy.mapping.Layer
        The arcpy Layer of the intersected polygons.

    Examples
    --------
    >>> from tidedates import utils
    >>> blobs = utils.intersect_polygon_layers(
    ...     "flood_damage_intersect.shp"
    ...     "floods.shp",
    ...     "wetlands.shp",
    ...     "buildings.shp"
    ... )

    """

    result = arcpy.analysis.Intersect(
        in_features=layers,
        out_feature_class=destination,
        **intersect_options
    )

    intersected = result_to_layer(result)
    return intersected


@update_status() # dict
def groupby_and_aggregate(input_path, groupfield, valuefield,
                          aggfxn=None):
    """
    Counts the number of distinct values of `valuefield` are associated
    with each value of `groupfield` in a data source found at
    `input_path`.

    Relies on `arcpy.da.TableToNumPyArray`_.

    .. _arcpy.da.TableToNumPyArray: http://resources.arcgis.com/en/help/main/10.2/index.html#/TableToNumPyArray/018w00000018000000/


    Parameters
    ----------
    input_path : str
        File path to a shapefile or feature class whose attribute table
        can be loaded with `arcpy.da.TableToNumPyArray`.
    groupfield : str
        The field name that would be used to group all of the records.
    valuefield : str
        The field name whose distinct values will be counted in each
        group defined by `groupfield`.
    aggfxn : callable, optional.
        Function to aggregate the values in each group to a single group.
        This function should accept an `itertools._grouper` as its only
        input. If not provided, unique number of value in the group will
        be returned.

    Returns
    -------
    counts : dict
        A dictionary whose keys are the distinct values of `groupfield`
        and values are the number of distinct records in each group.

    Examples
    --------
    >>> # compute total areas for each 'GeoID'
    >>> wetland_areas = utils.groupby_and_aggregate(
    ...     input_path='wetlands.shp',
    ...     groupfield='GeoID',
    ...     valuefield='SHAPE@AREA',
    ...     aggfxn=lambda group: sum([row[1] for row in group])
    ... )

    >>> # count the number of structures associated with each 'GeoID'
    >>> building_counts = utils.groupby_and_aggregate(
    ...     input_path=buildingsoutput,
    ...     groupfield=ID_column,
    ...     valuefield='STRUCT_ID'
    ... )

    See also
    --------
    itertools.groupby
    populate_field

    """

    if aggfxn is None:
        aggfxn = lambda x: int(numpy.unique(list(x)).shape[0])

    # load the data
    layer = load_data(input_path, "layer")

    # check that fields are valid
    _check_fields(layer.dataSource, groupfield, valuefield, should_exist=True)

    table = arcpy.da.TableToNumPyArray(layer, [groupfield, valuefield])
    #_status((table.dtype), verbose=True, asMessage=True)
    #table.sort(order=groupfield)
    table.sort()

    counts = {}
    for groupname, shapes in itertools.groupby(table, lambda row: row[groupfield]):
        #values  = numpy.unique(list(shapes))
        counts[groupname] = aggfxn(shapes)

    return counts


@update_status() # None
def rename_column(table, oldname, newname, newalias=None): # pragma: no cover
    """
    .. note: Not yet implemented.
    """
    raise NotImplementedError
    if newalias is None:
        newalias = newname

    oldfield = filter(
        lambda f: f.name == oldname,
        arcpy.ListFields(table)
    )[0]

    arcpy.management.AlterField(
        in_table=table,
        field=oldfield,
        new_field_name=newname,
        new_field_alias=newalias
    )


@update_status() # None
def populate_field(table, value_fxn, valuefield, *keyfields):
    """
    Loops through the records of a table and populates the value of one
    field (`valuefield`) based on another field (`keyfield`) by passing
    the entire row through a function (`value_fxn`).

    Relies on `arcpy.da.UpdateCursor`_.

    .. _arcpy.da.UpdateCursor: http://resources.arcgis.com/en/help/main/10.2/index.html#/UpdateCursor/018w00000014000000/

    Parameters
    ----------
    table : Layer, table, or file path
        This is the layer/file that will have a new field created.
    value_fxn : callable
        Any function that accepts a row from an `arcpy.da.SearchCursor`
        and returns a *single* value.
    valuefield : string
        The name of the field to be computed.
    *keyfields : strings, optional
        The other fields that need to be present in the rows of the
        cursor.

    Returns
    -------
    None

    .. note::
       In the row object, the `valuefield` will be the last item.
       In other words, `row[0]` will return the first values in
       `*keyfields` and `row[-1]` will return the existing value of
       `valuefield` in that row.

    Examples
    --------
    >>> # populate field ("Company") with a constant value ("Geosyntec")
    >>> populate_field("wetlands.shp", lambda row: "Geosyntec", "Company")

    """

    fields = list(keyfields)
    fields.append(valuefield)
    _check_fields(table, *fields, should_exist=True)

    with arcpy.da.UpdateCursor(table, fields) as cur:
        for row in cur:
            row[-1] = value_fxn(row)
            cur.updateRow(row)


@update_status() # layers
def copy_data(destfolder, *source_layers, **kwargs):
    """ Copies an arbitrary number of spatial files to a new folder.

    Relies on `arcpy.conversion.FeatureClassToShapefile`_.

    .. _arcpy.conversion.FeatureClassToShapefile: http://resources.arcgis.com/en/help/main/10.2/index.html#//00120000003m000000

    Parameters
    ----------
    destfolder : str
        Path the folder that is the destination for the files.
    *source_layers : str
        Paths to the files that need to be copied
    squeeze : bool, optional (False)
        When one layer is copied and this is True, the copied layer is
        returned. Otherwise, this function returns a list of layers.

    Returns
    -------
    copied : list of arcpy.mapping Layers or just a single Layer.

    """

    squeeze = kwargs.pop("squeeze", False)
    arcpy.conversion.FeatureClassToShapefile(
        Input_Features=source_layers,
        Output_Folder=destfolder
    )

    outputnames = [
        os.path.join(destfolder, os.path.basename(lyr))
        for lyr in source_layers
    ]

    copied = [load_data(name, "layer") for name in outputnames]
    if squeeze and len(copied) == 1:
        copied = copied[0]

    return copied


@update_status()
def concat_results(destination, *input_files):
    """ Concatentates (merges) serveral datasets into a single shapefile
    or feature class.

    Relies on `arcpy.management.Merge`_.

    .. _arcpy.management.Merge: http://resources.arcgis.com/en/help/main/10.2/index.html#//001700000055000000

    Parameters
    ----------
    destination : str
        Path to where the concatentated dataset should be saved.
    *input_files : str
        Strings of the paths of the datasets to be merged.

    Returns
    -------
    arcpy.mapping.Layer

    See also
    --------
    join_results_to_baseline

    """

    result = arcpy.management.Merge(input_files, destination)
    return result_to_layer(result)

@update_status()
def join_results_to_baseline(destination, result_file, baseline_file):
    """ Joins attributes of a geoprocessing result to a baseline dataset
    and saves the results to another file.

    Relies on `arcpy.analysis.SpatialJoin`_.

    .. _arcpy.analysis.SpatialJoin: http://resources.arcgis.com/en/help/main/10.2/index.html#//00080000000q000000

    Parameters
    ----------
    destination : str
        Path to where the final joined dataset should be saved.
    results_file : str
        Path to the results file whose attributes will be added to the
        ``baseline_file``.
    baseline_file : str
        Path to the baseline_file with the desired geometry.

    Returns
    -------
    arcpy.mapping.Layer

    See also
    --------
    concat_results

    """

    result = arcpy.analysis.SpatialJoin(
        target_features=baseline_file,
        join_features=result_file,
        out_feature_class=destination,
        join_operation="JOIN_ONE_TO_MANY",
        join_type="KEEP_COMMON",
        match_option="INTERSECT",
    )

    return result_to_layer(result)
