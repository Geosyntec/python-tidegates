import os
from pkg_resources import resource_filename
import time

import arcpy
import numpy

import nose.tools as nt
import numpy.testing as nptest
import tidegates.testing as tgtest
import mock

import tidegates
from tidegates import utils


@nt.nottest
class MockResult(object):
    def __init__(self, path):
        self.path = path

    def getOutput(*args, **kwargs):
        return self.path


class Test_EasyMapDoc(object):
    def setup(self):
        self.mxd = resource_filename("tidegates.testing.EasyMapDoc", "test.mxd")
        self.ezmd = utils.EasyMapDoc(self.mxd)

        self.knownlayer_names = ['ZOI', 'wetlands', 'ZOI_first_few', 'wetlands_first_few']
        self.knowndataframe_names = ['Main', 'Subset']
        self.add_layer_path = resource_filename("tidegates.testing.EasyMapDoc", "ZOI.shp")

    def test_layers(self):
        nt.assert_true(hasattr(self.ezmd, 'layers'))
        layers_names = [layer.name for layer in self.ezmd.layers]
        nt.assert_list_equal(layers_names, self.knownlayer_names)

    def test_dataframes(self):
        nt.assert_true(hasattr(self.ezmd, 'dataframes'))
        df_names = [df.name for df in self.ezmd.dataframes]
        nt.assert_list_equal(df_names, self.knowndataframe_names)

    def test_findLayerByName(self):
        name = 'ZOI_first_few'
        lyr = self.ezmd.findLayerByName(name)
        nt.assert_true(isinstance(lyr, arcpy.mapping.Layer))
        nt.assert_equal(lyr.name, name)

    def test_add_layer_with_path(self):
        nt.assert_equal(len(self.ezmd.layers), 4)
        self.ezmd.add_layer(self.add_layer_path)
        nt.assert_equal(len(self.ezmd.layers), 5)

    def test_add_layer_with_layer_and_other_options(self):
        layer = arcpy.mapping.Layer(self.add_layer_path)
        nt.assert_equal(len(self.ezmd.layers), 4)
        self.ezmd.add_layer(layer, position='bottom', df=self.ezmd.dataframes[1])
        nt.assert_equal(len(self.ezmd.layers), 5)

    @nt.raises(ValueError)
    def test_bad_layer(self):
        self.ezmd.add_layer(123456)

    @nt.raises(ValueError)
    def test_bad_position(self):
        self.ezmd.add_layer(self.add_layer_path, position='junk')


class Test_Extension(object):
    def setup(self):
        self.known_available = 'spatial'
        self.known_unavailable = 'Datareviewer'

    @nt.raises(RuntimeError)
    def test_unlicensed_extension(self):
        with utils.Extension(self.known_unavailable):
            pass

    def test_licensed_extension(self):
        nt.assert_equal(arcpy.CheckExtension(self.known_available), u'Available')
        with utils.Extension(self.known_available) as ext:
            nt.assert_equal(ext, 'CheckedOut')

        nt.assert_equal(arcpy.CheckExtension(self.known_available), u'Available')

    def teardown(self):
        arcpy.CheckExtension(self.known_available)


class Test_OverwriteState(object):
    def test_true_true(self):
        arcpy.env.overwriteOutput = True

        nt.assert_true(arcpy.env.overwriteOutput)
        with utils.OverwriteState(True):
            nt.assert_true(arcpy.env.overwriteOutput)

        nt.assert_true(arcpy.env.overwriteOutput)

    def test_false_false(self):
        arcpy.env.overwriteOutput = False

        nt.assert_false(arcpy.env.overwriteOutput)
        with utils.OverwriteState(False):
            nt.assert_false(arcpy.env.overwriteOutput)

        nt.assert_false(arcpy.env.overwriteOutput)

    def test_true_false(self):
        arcpy.env.overwriteOutput = True

        nt.assert_true(arcpy.env.overwriteOutput)
        with utils.OverwriteState(False):
            nt.assert_false(arcpy.env.overwriteOutput)

        nt.assert_true(arcpy.env.overwriteOutput)

    def test_false_true(self):
        arcpy.env.overwriteOutput = False

        nt.assert_false(arcpy.env.overwriteOutput)
        with utils.OverwriteState(True):
            nt.assert_true(arcpy.env.overwriteOutput)

        nt.assert_false(arcpy.env.overwriteOutput)


class Test_WorkSpace(object):
    def setup(self):
        self.baseline = os.getcwd()
        self.new_ws = u'C:/Users'

        arcpy.env.workspace = self.baseline

    def test_workspace(self):
        nt.assert_equal(arcpy.env.workspace, self.baseline)
        with utils.WorkSpace(self.new_ws):
            nt.assert_equal(arcpy.env.workspace, self.new_ws)

        nt.assert_equal(arcpy.env.workspace, self.baseline)


class Test_create_temp_filename():
    def setup(self):
        self.folderworkspace = os.path.join('some', 'other', 'folder')
        self.geodbworkspace = os.path.join('another', 'geodb.gdb')

    def test_folderworkspace_withsubfolder(self):
        with utils.WorkSpace(self.folderworkspace):
            known_raster = os.path.join(self.folderworkspace, 'subfolder', '_temp_test.tif')
            temp_raster = utils.create_temp_filename(os.path.join('subfolder', 'test'), filetype='raster')
            nt.assert_equal(temp_raster, known_raster)

            known_shape = os.path.join(self.folderworkspace, 'subfolder', '_temp_test.shp')
            temp_shape = utils.create_temp_filename(os.path.join('subfolder','test'), filetype='shape')
            nt.assert_equal(temp_shape, known_shape)

    def test_folderworkspace_barefile(self):
        with utils.WorkSpace(self.folderworkspace):
            known_raster = os.path.join(self.folderworkspace, '_temp_test.tif')
            temp_raster = utils.create_temp_filename('test', filetype='raster')
            nt.assert_equal(temp_raster, known_raster)

            known_shape = os.path.join(self.folderworkspace, '_temp_test.shp')
            temp_shape = utils.create_temp_filename('test', filetype='shape')
            nt.assert_equal(temp_shape, known_shape)

    def test_geodb_barefile(self):
        with utils.WorkSpace(self.geodbworkspace):
            known_raster = os.path.join(self.geodbworkspace, '_temp_test')
            temp_raster = utils.create_temp_filename('test', filetype='raster')
            nt.assert_equal(temp_raster, known_raster)

            known_shape = os.path.join(self.geodbworkspace, '_temp_test')
            temp_shape = utils.create_temp_filename('test', filetype='shape')
            nt.assert_equal(temp_shape, known_shape)

    def test_geodb_as_subfolder(self):
        with utils.WorkSpace(self.folderworkspace):
            filename = os.path.join(self.geodbworkspace, 'test')
            known_raster = os.path.join(self.folderworkspace, self.geodbworkspace, '_temp_test')
            temp_raster = utils.create_temp_filename(filename, filetype='raster')
            nt.assert_equal(temp_raster, known_raster)

            known_shape = os.path.join(self.folderworkspace, self.geodbworkspace, '_temp_test')
            temp_shape = utils.create_temp_filename(filename, filetype='shape')
            nt.assert_equal(temp_shape, known_shape)

    def test_with_extension_geodb(self):
        with utils.WorkSpace(self.folderworkspace):
            filename = os.path.join(self.geodbworkspace, 'test')
            known_raster = os.path.join(self.folderworkspace, self.geodbworkspace, '_temp_test')
            temp_raster = utils.create_temp_filename(filename + '.tif', filetype='raster')
            nt.assert_equal(temp_raster, known_raster)

            known_shape = os.path.join(self.folderworkspace, self.geodbworkspace, '_temp_test')
            temp_shape = utils.create_temp_filename(filename + '.tif', filetype='shape')
            nt.assert_equal(temp_shape, known_shape)

    def test_with_extension_folder(self):
        with utils.WorkSpace(self.folderworkspace):
            filename = 'test'
            known_raster = os.path.join(self.folderworkspace, '_temp_test.tif')
            temp_raster = utils.create_temp_filename(filename + '.tif', filetype='raster')
            nt.assert_equal(temp_raster, known_raster)

            known_shape = os.path.join(self.folderworkspace, '_temp_test.shp')
            temp_shape = utils.create_temp_filename(filename + '.shp', filetype='shape')
            nt.assert_equal(temp_shape, known_shape)


class Test__check_fields(object):
    table = resource_filename("tidegates.testing.check_fields", "test_file.shp")

    def test_should_exist_uni(self):
        utils._check_fields(self.table, "Id", should_exist=True)

    def test_should_exist_multi(self):
        utils._check_fields(self.table, "Id", "existing", should_exist=True)

    def test_should_exist_multi_witharea(self):
        utils._check_fields(self.table, "Id", "existing", "SHAPE@AREA", should_exist=True)

    @nt.raises(ValueError)
    def test_should_exist_bad_vals(self):
        utils._check_fields(self.table, "Id", "existing", "JUNK", "GARBAGE", should_exist=True)

    def test_should_not_exist_uni(self):
        utils._check_fields(self.table, "NEWFIELD", should_exist=False)

    def test_should_not_exist_multi(self):
        utils._check_fields(self.table, "NEWFIELD", "YANFIELD", should_exist=False)

    def test_should_not_exist_multi_witharea(self):
        utils._check_fields(self.table, "NEWFIELD", "YANFIELD", "SHAPE@AREA", should_exist=False)

    @nt.raises(ValueError)
    def test_should_not_exist_bad_vals(self):
        utils._check_fields(self.table, "NEWFIELD", "YANFIELD", "existing", should_exist=False)


def test_result_to_raster():
    mockResult = mock.Mock(spec=arcpy.Result)
    mockRaster = mock.Mock(spec=arcpy.Raster)
    with mock.patch('arcpy.Raster', mockRaster):
        raster = utils.result_to_raster(mockResult)
        mockResult.getOutput.assert_called_once_with(0)


def test_result_to_Layer():
    mockResult = mock.Mock(spec=arcpy.Result)
    mockLayer = mock.Mock(spec=arcpy.mapping.Layer)
    with mock.patch('arcpy.mapping.Layer', mockLayer):
        layer = utils.result_to_layer(mockResult)
        mockResult.getOutput.assert_called_once_with(0)


class Test_rasters_to_arrays(object):
    def setup(self):
        from numpy import nan
        self.known_array1 = numpy.array([
            [ 0.0,  1.0,  2.0,  3.0,  4.0],
            [ 5.0,  6.0,  7.0,  8.0,  9.0],
            [10.0, 11.0, 12.0, 13.0, 14.0],
            [15.0, 16.0, 17.0, 18.0, 19.0]
        ])

        self.known_array2 = numpy.array([
            [nan,  10.0,  20.0,  30.0,  40.0],
            [nan,  60.0,  70.0,  80.0,  90.0],
            [nan, 110.0, 120.0, 130.0, 140.0],
            [nan, 160.0, 170.0, 180.0, 190.0]
        ])

        self.known_array3 = numpy.array([
            [  00,  100,  200,  300,  400],
            [ 500,  600,  700,  800,  900],
            [1000, 1100, 1200, 1300, 1400],
            [1500, 1600, 1700, 1800, 1900]
        ])

        self.rasterfile1 = resource_filename("tidegates.testing.rasters_to_arrays", 'test_raster1')
        self.rasterfile2 = resource_filename("tidegates.testing.rasters_to_arrays", 'test_raster2')
        self.rasterfile3 = resource_filename("tidegates.testing.rasters_to_arrays", 'test_raster3')

    def test_one_raster(self):
        array = utils.rasters_to_arrays(self.rasterfile1)
        nt.assert_true(isinstance(array, list))
        nt.assert_equal(len(array), 1)
        nptest.assert_array_almost_equal(array[0], self.known_array1)

    def test_one_raster_squeezed(self):
        array = utils.rasters_to_arrays(self.rasterfile1, squeeze=True)
        nt.assert_true(isinstance(array, numpy.ndarray))
        nptest.assert_array_almost_equal(array, self.known_array1)

    def test_with_missing_values_squeeze(self):
        array = utils.rasters_to_arrays(self.rasterfile2, squeeze=True)
        nt.assert_true(isinstance(array, numpy.ndarray))
        nptest.assert_array_almost_equal(array, self.known_array2)

    def test_int_array(self):
        array = utils.rasters_to_arrays(self.rasterfile3, squeeze=True)
        nt.assert_true(isinstance(array, numpy.ndarray))
        nptest.assert_array_almost_equal(array, self.known_array3)

    def test_multiple_args(self):
        arrays = utils.rasters_to_arrays(
            self.rasterfile1,
            self.rasterfile2,
            self.rasterfile3,
            squeeze=True
        )

        nt.assert_true(isinstance(arrays, list))
        nt.assert_equal(len(arrays), 3)

        for a, kn in zip(arrays, [self.known_array1, self.known_array2, self.known_array3]):
            nt.assert_true(isinstance(a, numpy.ndarray))
            nptest.assert_array_almost_equal(a, kn)


def test_array_to_raster():
    template_file = resource_filename("tidegates.testing.array_to_raster", 'test_raster2')
    template = arcpy.Raster(template_file)
    array = numpy.arange(5, 25).reshape(4, 5).astype(float)

    raster = utils.array_to_raster(array, template)
    nt.assert_true(isinstance(raster, arcpy.Raster))
    nt.assert_true(raster.extent.equals(template.extent))
    nt.assert_equal(raster.meanCellWidth, template.meanCellWidth)
    nt.assert_equal(raster.meanCellHeight, template.meanCellHeight)


class Test_load_data(object):
    rasterpath = resource_filename("tidegates.testing.load_data", 'test_dem.tif')
    vectorpath = resource_filename("tidegates.testing.load_data", 'test_wetlands.shp')

    @nt.raises(ValueError)
    def test_bad_datatype(self):
        utils.load_data(self.rasterpath, 'JUNK')

    @nt.raises(ValueError)
    def test_datapath_doesnt_exist(self):
        utils.load_data('junk.shp', 'grid')

    @nt.raises(ValueError)
    def test_datapath_bad_value(self):
        utils.load_data(12345, 'grid')

    @nt.raises(ValueError)
    def test_vector_as_grid_should_fail(self):
        x = utils.load_data(self.vectorpath, 'grid')

    @nt.raises(ValueError)
    def test_vector_as_raster_should_fail(self):
        x = utils.load_data(self.vectorpath, 'raster')

    def test_raster_as_raster(self):
        x = utils.load_data(self.rasterpath, 'raster')
        nt.assert_true(isinstance(x, arcpy.Raster))

    def test_raster_as_grid_with_caps(self):
        x = utils.load_data(self.rasterpath, 'gRId')
        nt.assert_true(isinstance(x, arcpy.Raster))

    def test_raster_as_layer_not_greedy(self):
        x = utils.load_data(self.rasterpath, 'layer', greedyRasters=False)
        nt.assert_true(isinstance(x, arcpy.mapping.Layer))

    def test_raster_as_layer_greedy(self):
        x = utils.load_data(self.rasterpath, 'layer')
        nt.assert_true(isinstance(x, arcpy.Raster))

    def test_vector_as_shape(self):
        x = utils.load_data(self.vectorpath, 'shape')
        nt.assert_true(isinstance(x, arcpy.mapping.Layer))

    def test_vector_as_layer_with_caps(self):
        x = utils.load_data(self.vectorpath, 'LAyeR')
        nt.assert_true(isinstance(x, arcpy.mapping.Layer))

    def test_already_a_layer(self):
        lyr = arcpy.mapping.Layer(self.vectorpath)
        x = utils.load_data(lyr, 'layer')
        nt.assert_equal(x, lyr)

    def test_already_a_raster(self):
        raster = arcpy.Raster(self.rasterpath)
        x = utils.load_data(raster, 'raster')
        nt.assert_true(isinstance(x, arcpy.Raster))

        nptest.assert_array_almost_equal(*utils.rasters_to_arrays(x, raster))


class _polygons_to_raster_mixin(object):
    testfile = resource_filename("tidegates.testing.polygons_to_raster", "test_zones.shp")
    known_values = numpy.array([-999, 16, 150])

    def test_process(self):
        raster = utils.polygons_to_raster(self.testfile, "GeoID", **self.kwargs)
        nt.assert_true(isinstance(raster, arcpy.Raster))

        array = utils.rasters_to_arrays(raster, squeeze=True)
        arcpy.management.Delete(raster)

        flat_arr = array.flatten()
        bins = numpy.bincount(flat_arr[flat_arr > 0])
        nptest.assert_array_almost_equal(numpy.unique(array), self.known_values)
        nptest.assert_array_almost_equal(bins[bins > 0], self.known_counts)
        nt.assert_tuple_equal(array.shape, self.known_shape)


class Test_polygons_to_raster_default(_polygons_to_raster_mixin):
    def setup(self):
        self.kwargs = {}
        self.known_shape = (854, 661)
        self.known_counts = numpy.array([95274, 36674])


class Test_polygons_to_raster_x02(_polygons_to_raster_mixin):
    def setup(self):
        self.kwargs = {'cellsize': 2}
        self.known_shape = (1709, 1322)
        self.known_counts = numpy.array([381211, 146710])


class Test_polygons_to_raster_x08(_polygons_to_raster_mixin):
    def setup(self):
        self.kwargs = {'cellsize': 8}
        self.known_shape = (427, 330)
        self.known_counts = numpy.array([23828,  9172])

    def test_actual_arrays(self):
        known_raster_file = resource_filename("tidegates.testing.polygons_to_raster", "test_zones_raster.tif")
        known_raster = utils.load_data(known_raster_file, 'raster')
        raster = utils.polygons_to_raster(self.testfile, "GeoID", **self.kwargs)
        arrays = utils.rasters_to_arrays(raster, known_raster)
        arcpy.management.Delete(raster)

        nptest.assert_array_almost_equal(*arrays)


class Test_polygons_to_raster_x16(_polygons_to_raster_mixin):
    def setup(self):
        self.kwargs = {'cellsize': 16}
        self.known_shape = (214, 165)
        self.known_counts = numpy.array([5953, 2288])


def test_clip_dem_to_zones():
    demfile = resource_filename("tidegates.testing.clip_dem_to_zones", 'test_dem.tif')
    zonefile = resource_filename("tidegates.testing.clip_dem_to_zones", "test_zones_raster_small.tif")
    raster = utils.clip_dem_to_zones(demfile, zonefile)

    zone_r = utils.load_data(zonefile, 'raster')

    arrays = utils.rasters_to_arrays(raster, zone_r)

    dem_a, zone_a = arrays[0], arrays[1]
    arcpy.management.Delete(raster)

    nt.assert_true(isinstance(raster, arcpy.Raster))

    known_shape = (146, 172)
    nt.assert_tuple_equal(dem_a.shape, zone_a.shape)


@nptest.dec.skipif(not tgtest.has_fiona)
def test_raster_to_polygons():
    zonefile = resource_filename("tidegates.testing.raster_to_polygons", "input_raster_to_polygon.tif")
    knownfile = resource_filename("tidegates.testing.raster_to_polygons", "known_polygons_from_raster_1.shp")
    testfile = resource_filename("tidegates.testing.raster_to_polygons", "test_polygons_from_raster_1.shp")

    with utils.OverwriteState(True):
        zones = utils.load_data(zonefile, 'raster')
        known = utils.load_data(knownfile, 'layer')
        test = utils.raster_to_polygons(zones, testfile)

    tgtest.assert_shapefiles_are_close(test.dataSource, known.dataSource)
    utils.cleanup_temp_results(testfile)


@nptest.dec.skipif(not tgtest.has_fiona)
def test_raster_to_polygons_with_new_field():
    zonefile = resource_filename("tidegates.testing.raster_to_polygons", "input_raster_to_polygon.tif")
    knownfile = resource_filename("tidegates.testing.raster_to_polygons", "known_polygons_from_raster_2.shp")
    testfile = resource_filename("tidegates.testing.raster_to_polygons", "test_polygons_from_raster_2.shp")

    with utils.OverwriteState(True):
        zones = utils.load_data(zonefile, 'raster')
        known = utils.load_data(knownfile, 'layer')
        test = utils.raster_to_polygons(zones, testfile, newfield="GeoID")

    tgtest.assert_shapefiles_are_close(test.dataSource, known.dataSource)
    utils.cleanup_temp_results(testfile)


@nptest.dec.skipif(not tgtest.has_fiona)
def test_aggregate_polygons():
    inputfile = resource_filename("tidegates.testing.aggregate_polygons", "input_polygons_from_raster.shp")
    knownfile = resource_filename("tidegates.testing.aggregate_polygons", "known_dissolved_polygons.shp")
    testfile = resource_filename("tidegates.testing.aggregate_polygons", "test_dissolved_polygons.shp")

    with utils.OverwriteState(True):
        raw = utils.load_data(inputfile, 'layer')
        known = utils.load_data(knownfile, 'layer')
        test = utils.aggregate_polygons(raw, "gridcode", testfile)

    tgtest.assert_shapefiles_are_close(test.dataSource, known.dataSource)

    utils.cleanup_temp_results(testfile)


def test_mask_array_with_flood():
    zones = numpy.array([
        [  1,   1,   1,   1,   1,   1,   1,   1,   1,   1,   0],
        [  1,   1,   1,   1,   1,   1,   1,   1,   1,   1,   0],
        [  1,   1,   1,   1,   1,   1,   0,   0,   0,   0,   0],
        [  1,   1,   1,   1,   2,   2,   2,   2,   0,   0,   0],
        [  0,   0,   0,   2,   2,   2,   2,   0,   0,   0,   0],
        [  2,   2,   2,   2,   2,   2,   2,   0,   0,   0,   0],
        [  2,   2,   2,   2,   0,   0,   0,   0,   0,   0,   0],
        [  0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0],
        [  0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0],
        [  0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0],
        [  0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0],
    ])

    topo = numpy.array([
        [ 0.,  1.,  2.,  3.,  4.,  5.,  6.,  7.,  8.,  9., 10.],
        [ 1.,  2.,  3.,  4.,  5.,  6.,  7.,  8.,  9., 10., 11.],
        [ 2.,  3.,  4.,  5.,  6.,  7.,  8.,  9., 10., 11., 12.],
        [ 3.,  4.,  5.,  6.,  7.,  8.,  9., 10., 11., 12., 13.],
        [ 4.,  5.,  6.,  7.,  8.,  9., 10., 11., 12., 13., 14.],
        [ 5.,  6.,  7.,  8.,  9., 10., 11., 12., 13., 14., 15.],
        [ 6.,  7.,  8.,  9., 10., 11., 12., 13., 14., 15., 16.],
        [ 7.,  8.,  9., 10., 11., 12., 13., 14., 15., 16., 17.],
        [ 8.,  9., 10., 11., 12., 13., 14., 15., 16., 17., 18.],
        [ 9., 10., 11., 12., 13., 14., 15., 16., 17., 18., 19.],
        [10., 11., 12., 13., 14., 15., 16., 17., 18., 19., 20.],
    ])

    known_flooded = numpy.array([
        [  1,   1,   1,   1,   1,   1,   1,   0,   0,   0,   0],
        [  1,   1,   1,   1,   1,   1,   0,   0,   0,   0,   0],
        [  1,   1,   1,   1,   1,   0,   0,   0,   0,   0,   0],
        [  1,   1,   1,   1,   0,   0,   0,   0,   0,   0,   0],
        [  0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0],
        [  2,   2,   0,   0,   0,   0,   0,   0,   0,   0,   0],
        [  2,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0],
        [  0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0],
        [  0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0],
        [  0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0],
        [  0,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0],
    ])

    flooded = utils.flood_zones(zones, topo, 6.0)
    nptest.assert_array_almost_equal(flooded, known_flooded)


class Test_add_field_with_value(object):
    def setup(self):
        self.shapefile = resource_filename("tidegates.testing.add_field_with_value", 'field_adder.shp')
        self.fields_added = ["_text", "_unicode", "_int", "_float", '_no_valstr', '_no_valnum']

    def teardown(self):
        field_names = [f.name for f in arcpy.ListFields(self.shapefile)]
        for field in self.fields_added:
            if field in field_names:
                arcpy.management.DeleteField(self.shapefile, field)

    def test_float(self):
        name = "_float"
        utils.add_field_with_value(self.shapefile, name,
                                   field_value=5.0)
        nt.assert_true(name in [f.name for f in arcpy.ListFields(self.shapefile)])

        newfield = arcpy.ListFields(self.shapefile, name)[0]
        nt.assert_equal(newfield.type, u'Double')

    def test_int(self):
        name = "_int"
        utils.add_field_with_value(self.shapefile, name,
                                   field_value=5)
        nt.assert_true(name in [f.name for f in arcpy.ListFields(self.shapefile)])

        newfield = arcpy.ListFields(self.shapefile, name)[0]
        nt.assert_equal(newfield.type, u'Integer')

    def test_string(self):
        name = "_text"
        utils.add_field_with_value(self.shapefile, name,
                                   field_value="example_value",
                                   field_length=15)

        nt.assert_true(name in [f.name for f in arcpy.ListFields(self.shapefile)])

        newfield = arcpy.ListFields(self.shapefile, name)[0]
        nt.assert_equal(newfield.type, u'String')
        nt.assert_true(newfield.length, 15)

    def test_unicode(self):
        name = "_unicode"
        utils.add_field_with_value(self.shapefile, name,
                                   field_value=u"example_value",
                                   field_length=15)

        nt.assert_true(name in [f.name for f in arcpy.ListFields(self.shapefile)])

        newfield = arcpy.ListFields(self.shapefile, name)[0]
        nt.assert_equal(newfield.type, u'String')
        nt.assert_true(newfield.length, 15)

    def test_no_value_string(self):
        name = "_no_valstr"
        utils.add_field_with_value(self.shapefile, name,
                                   field_type='TEXT',
                                   field_length=15)

        nt.assert_true(name in [f.name for f in arcpy.ListFields(self.shapefile)])

        newfield = arcpy.ListFields(self.shapefile, name)[0]
        nt.assert_equal(newfield.type, u'String')
        nt.assert_true(newfield.length, 15)

    def test_no_value_number(self):
        name = "_no_valnum"
        utils.add_field_with_value(self.shapefile, name,
                                   field_type='DOUBLE')

        nt.assert_true(name in [f.name for f in arcpy.ListFields(self.shapefile)])

        newfield = arcpy.ListFields(self.shapefile, name)[0]
        nt.assert_equal(newfield.type, u'Double')

    @nt.raises(ValueError)
    def test_no_value_no_field_type(self):
        utils.add_field_with_value(self.shapefile, "_willfail")

    @nt.raises(ValueError)
    def test_overwrite_existing_no(self):
        utils.add_field_with_value(self.shapefile, "existing")

    def test_overwrite_existing_yes(self):
        utils.add_field_with_value(self.shapefile, "existing",
                                   overwrite=True,
                                   field_type="LONG")


class Test_cleanup_temp_results(object):
    def setup(self):
        self.workspace = os.path.abspath(resource_filename('tidegates.testing', 'cleanup_temp_results'))
        self.template_file = resource_filename('tidegates.testing.cleanup_temp_results', 'test_dem.tif')
        self.template = utils.load_data(self.template_file, 'raster')

        raster1 = utils.array_to_raster(numpy.random.normal(size=(30, 30)), self.template)
        raster2 = utils.array_to_raster(numpy.random.normal(size=(60, 60)), self.template)

        self.name1 = 'temp_1.tif'
        self.name2 = 'temp_2.tif'

        self.path1 = os.path.join(self.workspace, self.name1)
        self.path2 = os.path.join(self.workspace, self.name2)

        with utils.OverwriteState(True), utils.WorkSpace(self.workspace):
            raster1.save(self.path1)
            raster2.save(self.path2)

    @nt.nottest
    def check_outcome(self):
        nt.assert_false(os.path.exists(os.path.join(self.workspace, 'temp_1.tif')))
        nt.assert_false(os.path.exists(os.path.join(self.workspace, 'temp_2.tif')))

    def test_with_names_in_a_workspace(self):
        with utils.WorkSpace(self.workspace):
            utils.cleanup_temp_results(self.name1, self.name2)
            self.check_outcome()

    def test_with_paths_absolute(self):
        utils.cleanup_temp_results(self.path1, self.path2)
        self.check_outcome()

    def test_with_rasters(self):
        with utils.WorkSpace(self.workspace):
            raster1 = utils.load_data(self.path1, 'raster')
            raster2 = utils.load_data(self.path2, 'raster')
            utils.cleanup_temp_results(raster1, raster2)
            self.check_outcome()

    def test_with_results(self):
        with utils.WorkSpace(self.workspace):
            res1 = arcpy.Result(toolname='Clip_management')
            res2 = arcpy.Result(toolname='Clip_management')
            with mock.patch.object(res1, 'getOutput', return_value='temp_1.tif'), \
                 mock.patch.object(res2, 'getOutput', return_value='temp_2.tif'):
                utils.cleanup_temp_results(res1, res2)
                self.check_outcome()

    def test_with_layers(self):
        with utils.WorkSpace(self.workspace):
            lyr1 = utils.load_data('temp_1.tif', 'layer', greedyRasters=False)
            lyr2 = utils.load_data('temp_2.tif', 'layer', greedyRasters=False)
            utils.cleanup_temp_results(lyr1, lyr2)
            self.check_outcome()

    @nt.raises(ValueError)
    def test_with_bad_input(self):
        utils.cleanup_temp_results(1, 2, ['a', 'b', 'c'])

    def teardown(self):
        with utils.WorkSpace(self.workspace):
            utils.cleanup_temp_results('temp_1.tif', 'temp_2.tif')


@nptest.dec.skipif(not tgtest.has_fiona)
def test_intersect_polygon_layers():
    input1_file = resource_filename("tidegates.testing.intersect_polygons", "intersect_input1.shp")
    input2_file = resource_filename("tidegates.testing.intersect_polygons", "intersect_input2.shp")
    known_file = resource_filename("tidegates.testing.intersect_polygons", "intersect_known.shp")
    output_file = resource_filename("tidegates.testing.intersect_polygons", "intersect_output.shp")

    with utils.OverwriteState(True):
        output = utils.intersect_polygon_layers(
            output_file,
            input1_file,
            input2_file,
        )

    nt.assert_true(isinstance(output, arcpy.mapping.Layer))
    tgtest.assert_shapefiles_are_close(output_file, known_file)

    utils.cleanup_temp_results(output)


class Test_groupby_and_aggregate():
    known_counts = {16.0: 32, 150.0: 2}
    buildings = resource_filename("tidegates.testing.groupby_and_aggregate", "flooded_buildings.shp")
    group_col = 'GeoID'
    count_col = 'STRUCT_ID'
    area_op = 'SHAPE@AREA'

    areas = resource_filename("tidegates.testing.groupby_and_aggregate", "intersect_input1.shp")
    known_areas = {2: 1327042.1024, 7: 1355433.0192, 12: 1054529.2882}

    def test_defaults(self):
        counts = utils.groupby_and_aggregate(
            self.buildings,
            self.group_col,
            self.count_col,
            aggfxn=None
        )

        nt.assert_dict_equal(counts, self.known_counts)

    def test_area(self):
        areadict = utils.groupby_and_aggregate(
            self.areas,
            self.group_col,
            self.area_op,
            aggfxn=lambda g: sum([row[1] for row in g])
        )
        for key in areadict.keys():
            nt.assert_almost_equal(
                areadict[key],
                self.known_areas[key],
                delta=0.01
            )

    def test_recarry_sort_no_args(self):
        known = numpy.array([
            ('A', 1.), ('A', 2.), ('A', 3.), ('A', 4.),
            ('B', 1.), ('B', 2.), ('B', 3.), ('B', 4.),
            ('C', 1.), ('C', 2.), ('C', 3.), ('C', 4.),
        ], dtype=[('GeoID', 'S4'), ('Area', float)])

        test = numpy.array([
            ('A', 1.), ('B', 1.), ('C', 3.), ('A', 4.),
            ('C', 4.), ('A', 2.), ('C', 1.), ('A', 3.),
            ('B', 2.), ('C', 2.), ('B', 4.), ('B', 3.),
        ], dtype=[('GeoID', 'S4'), ('Area', float)])

        test.sort()
        nptest.assert_array_equal(test, known)

    @nt.raises(ValueError)
    def test_bad_group_col(self):
        counts = utils.groupby_and_aggregate(
            self.buildings,
            "JUNK",
            self.count_col
        )

    @nt.raises(ValueError)
    def test_bad_count_col(self):
        counts = utils.groupby_and_aggregate(
            self.buildings,
            self.group_col,
            "JUNK"
        )


@nt.raises(NotImplementedError)
def test_rename_column():
    layer = resource_filename("tidegates.testing.rename_column", "rename_col.dbf")
    oldname = "existing"
    newname = "exists"

    #layer = utils.load_data(inputfile, "layer")

    utils.rename_column(layer, oldname, newname)
    utils._check_fields(layer, newname, should_exist=True)
    utils._check_fields(layer, oldname, should_exist=False)

    utils.rename_column(layer, newname, oldname)
    utils._check_fields(layer, newname, should_exist=False)
    utils._check_fields(layer, oldname, should_exist=True)


class Test_populate_field(object):
    def setup(self):
        self.shapefile = resource_filename("tidegates.testing.populate_field", 'populate_field.shp')
        self.field_added = "newfield"

    def teardown(self):
        arcpy.management.DeleteField(self.shapefile, self.field_added)

    def test_with_dictionary(self):
        value_dict = {n: n for n in range(7)}
        value_fxn = lambda row: value_dict.get(row[0], -1)
        utils.add_field_with_value(self.shapefile, self.field_added, field_type="LONG")

        utils.populate_field(
            self.shapefile,
            lambda row: value_dict.get(row[0], -1),
            self.field_added,
            "FID"
        )

        with arcpy.da.SearchCursor(self.shapefile, [self.field_added, "FID"]) as cur:
            for row in cur:
                nt.assert_equal(row[0], row[1])

    def test_with_general_function(self):
        utils.add_field_with_value(self.shapefile, self.field_added, field_type="LONG")
        utils.populate_field(
            self.shapefile,
            lambda row: row[0]**2,
            self.field_added,
            "FID"
        )

        with arcpy.da.SearchCursor(self.shapefile, [self.field_added, "FID"]) as cur:
            for row in cur:
                nt.assert_equal(row[0], row[1] ** 2)


class Test_copy_data(object):
    destfolder = resource_filename("tidegates.testing.copy_data", "output")
    srclayers = [
        resource_filename("tidegates.testing.copy_data", "copy2.shp"),
        resource_filename("tidegates.testing.copy_data", "copy1.shp"),
    ]

    output = [
        resource_filename("tidegates.testing.copy_data.output", "copy2.shp"),
        resource_filename("tidegates.testing.copy_data.output", "copy1.shp"),
    ]

    def teardown(self):
        utils.cleanup_temp_results(*self.output)


    @nptest.dec.skipif(not tgtest.has_fiona)
    def test_list(self):
        with utils.OverwriteState(True):
            newlayers = utils.copy_data(self.destfolder, *self.srclayers)

        nt.assert_true(isinstance(newlayers, list))

        for newlyr, newname, oldname in zip(newlayers, self.output, self.srclayers):
            nt.assert_true(isinstance(newlyr, arcpy.mapping.Layer))
            tgtest.assert_shapefiles_are_close(newname, oldname)

    @nptest.dec.skipif(not tgtest.has_fiona)
    def test_single_squeeze_false(self):
        with utils.OverwriteState(True):
            newlayers = utils.copy_data(self.destfolder, *self.srclayers[:1])

        nt.assert_true(isinstance(newlayers, list))

        for newlyr, newname, oldname in zip(newlayers[:1], self.output[:1], self.srclayers[:1]):
            nt.assert_true(isinstance(newlyr, arcpy.mapping.Layer))
            tgtest.assert_shapefiles_are_close(newname, oldname)

    @nptest.dec.skipif(not tgtest.has_fiona)
    def test_single_squeeze_true(self):
        with utils.OverwriteState(True):
            newlayer = utils.copy_data(self.destfolder, *self.srclayers[:1], squeeze=True)

        nt.assert_true(isinstance(newlayer, arcpy.mapping.Layer))

        nt.assert_true(isinstance(newlayer, arcpy.mapping.Layer))
        tgtest.assert_shapefiles_are_close(self.output[0], self.srclayers[0])


@nptest.dec.skipif(not tgtest.has_fiona)
def test_concat_results():
    known = resource_filename('tidegates.testing.concat_results', 'known.shp')
    with utils.OverwriteState(True):
        test = utils.concat_results(
            resource_filename('tidegates.testing.concat_results', 'result.shp'),
            resource_filename('tidegates.testing.concat_results', 'input1.shp'),
            resource_filename('tidegates.testing.concat_results', 'input2.shp')
        )

    nt.assert_true(isinstance(test, arcpy.mapping.Layer))
    tgtest.assert_shapefiles_are_close(test.dataSource, known)

    utils.cleanup_temp_results(test)


@nptest.dec.skipif(not tgtest.has_fiona)
def test_join_results_to_baseline():
    known = resource_filename('tidegates.testing.join_results', 'merge_result.shp')
    with utils.OverwriteState(True):
        test = utils.join_results_to_baseline(
            resource_filename('tidegates.testing.join_results', 'merge_result.shp'),
            resource_filename('tidegates.testing.join_results', 'merge_join.shp'),
            resource_filename('tidegates.testing.join_results', 'merge_baseline.shp')
        )
    nt.assert_true(isinstance(test, arcpy.mapping.Layer))
    tgtest.assert_shapefiles_are_close(test.dataSource, known)

    utils.cleanup_temp_results(test)

