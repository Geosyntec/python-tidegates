import os
import sys
import glob
import datetime
from functools import wraps
import itertools

import numpy

import arcpy


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


def _status(msg, verbose=False, asMessage=False, addTab=False): # pragma: no cover
    if verbose:
        if addTab:
            msg = '\t' + msg
        if asMessage:
            arcpy.AddMessage(msg)
        else:
            print(msg)


def update_status(): # pragma: no cover
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
    file_with_ext = os.path.basename(filepath)
    folder = os.path.dirname(filepath)
    return os.path.join(folder, prefix + file_with_ext)


def _check_fields(table, *fieldnames, **kwargs):
    """
    Checks that field are (or are not) in a table. The check fails, a
    `ValueError` is raised.

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
        qual = " not "
    else:
        qual = ' '

    if len(bad_names) > 0:
        raise ValueError('fields {} are{}in {}'.format(bad_names, qual, table))


@update_status() # raster
def result_to_raster(result):
    """ Gets the actual raster from an arcpy.Result object """
    return arcpy.Raster(result.getOutput(0))


@update_status() # layer
def result_to_layer(result):
    """ Gets the actual layer from an arcpy.Result object """
    return arcpy.mapping.Layer(result.getOutput(0))


@update_status() # list of arrays
def rasters_to_arrays(*rasters, **kwargs):
    """ Converts an arbitrary number of rasters to numpy arrays"""
    squeeze = kwargs.pop("squeeze", False)

    arrays = []
    for n, r in enumerate(rasters):
        arrays.append(arcpy.RasterToNumPyArray(r, nodata_to_value=-999))

    if squeeze and len(arrays) == 1:
        arrays = arrays[0]

    return arrays


@update_status() # raster
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


@update_status() # raster or layer
def load_data(datapath, datatype, greedyRasters=True, **verbosity):
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


@update_status() # raster and result
def process_polygons(polygons, ID_column, cellsize=4):
    """ Prepare tidegates' areas of influence polygons for flooding
    by converting to a raster.

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

    """

    _zones = load_data(polygons, 'shape')

    with OverwriteState(True), Extension("spatial"):
        result = arcpy.conversion.PolygonToRaster(
            in_features=_zones,
            value_field=ID_column,
            cellsize=cellsize,
        )

    # result object isn't actually the raster
    # need to read in the raster as an object
    # the file path embedded in the result
    zones = result_to_raster(result)

    return zones, result


@update_status() # raster and result
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


@update_status() # layer
def raster_to_polygons(zonal_raster, filename):
    """
    Converts zonal rasters to polygons layers. This is basically just
    a thing wrapper around arcpy.conversion.RasterToPolygon. The
    returned layers will have a field "gridcode" that corresponds to the
    values of the raster.

    Parameters
    ----------
    zonal_raster : arcpy.Raster
        An integer raster of reasonably small set distinct values.
    filename : str
        Path to where the polygons will be saved.

    Returns
    -------
    polygons : arcpy.mapping.Layer
        The converted polygons.

    See Also
    --------
    arcpy.conversion.RasterToPolygon

    """

    results = arcpy.conversion.RasterToPolygon(
        in_raster=zonal_raster,
        out_polygon_features=filename,
        simplify="SIMPLIFY",
        raster_field="Value",
    )

    polygons = result_to_layer(results)
    return polygons


@update_status() # layer
def aggregate_polygons(polygons, ID_field, filename):
    """
    Dissolves (aggregates) polygons into a single feature the unique
    values in the provided field. This is basically just a thim wrapper
    around `arcpy.management.Dissolve`.

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


@update_status() # None
def add_field_with_value(table, field_name, field_value=None,
                         overwrite=False, **field_opts):
    """ Adds a numeric or text field to an attribute table and sets it
    to a constant value. Operates in-place and therefore does not
    return anything.

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
    **field_opts : keyword options
        Keyword arguments that are passed directly to
        `arcpy.management.AddField`.

    Returns
    -------
    None

    See Also
    --------
    `arcpy.management.AddField`

    Examples
    --------
    >>> # add a text field to shapefile (text fields need a length speci)
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
    for r in results:
        arcpy.management.Delete(r)


@update_status() # layer
def intersect_polygon_layers(*layers, **intersect_options):
    """
    Intersect polygon layers with each other. Basically a thin wrapper
    around `arcpy.analysis.Intersect`.

    Parameters
    ----------
    *layers : string or `arcpy.Mapping.layers
        The polyong layers (or their paths) that will be intersected
        with each other.
    filename : str
        Filepath where the intersected output will be saved.
    **intersect_options : keyword arguments
        Additional arguments that will be passed directly to
        `arcpy.analysis.Intersect`.

    Returns
    -------
    intersected : arcpy.mapping.Layer
        The arcpy Layer of the intersected polygons.

    Example
    -------
    >>> from tidedates import utils
    >>> blobs = utils.intersect_polygon_layers(
    >>> ...     "floods.shp",
    >>> ...     "wetlands.shp",
    >>> ...     "buildings.shp"
    >>> ...     filename="flood_damage.shp"
    >>> ... )

    """

    output = intersect_options.pop("filename", None)
    if output is None:
        msg = "named argument `filename` required for intersect_polygon_layers"
        raise ValueError(msg)

    result = arcpy.analysis.Intersect(
        in_features=layers,
        out_feature_class=output,
        **intersect_options
    )

    intersected = result_to_layer(result)
    return intersected


@update_status() # dict
def groupby_and_count(input_path, groupfield, countfield):
    """
    Counts the number of distinct values of `countfield` are associated
    with each value of `groupfield` in a data source found at
    `input_path`.

    Parameters
    ----------
    input_path : str
        File path to a shapefile or feature class whose attribute table
        can be loaded with `arcpy.da.TableToNumPyArray`.
    groupfield : str
        The field name that would be used to group all of the records.
    countfield : str
        The field name whose distinct values will be counted in each
        group defined by `groupfield`.

    Returns
    -------
    counts : dict
        A dictionary whose keys are the distinct values of `groupfield`
        and values are the number of distinct records in each group.

    See Also
    --------
    `arcpy.da.TableToNumPyArray`
    `itertools.groupby`

    """

    # load the data
    layer = load_data(input_path, "layer")

    # check that fields are valid
    _check_fields(layer.dataSource, groupfield, countfield, should_exist=True)

    table = arcpy.da.TableToNumPyArray(layer, [groupfield, countfield])
    table.sort(order=groupfield)

    counts = {}
    for groupname, shapes in itertools.groupby(table, lambda row: row[groupfield]):
        values  = numpy.unique(list(shapes))
        counts[groupname] = int(values.shape[0])

    return counts


@update_status() # None
def rename_column(table, oldname, newname, newalias=None): # pragma: no cover
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

    Notes
    -----
    In the row object, the `valuefield` will be the last item. In other
    words, `row[0]` will return the first values in `*keyfields` and
    `row[-1]` will return the existing value of `valuefield` in that
    row.

    """

    fields = list(keyfields)
    fields.append(valuefield)
    _check_fields(table, *fields, should_exist=True)

    with arcpy.da.UpdateCursor(table, fields) as cur:
        for row in cur:
            row[-1] = value_fxn(row)
            cur.updateRow(row)
