import os
from pkg_resources import resource_filename

import arcpy
import numpy

import nose.tools as nt
import numpy.testing as nptest
import tidegates.testing as tgtest
import mock

import tidegates
from tidegates import utils





class Test_EasyMapDoc(object):
    def setup(self):
        self.mxd = resource_filename("tidegates.testing", "test.mxd")
        self.ezmd = utils.EasyMapDoc(self.mxd)

        self.knownlayer_names = ['ZOI', 'wetlands', 'ZOI_first_few', 'wetlands_first_few']
        self.knowndataframe_names = ['Main', 'Subset']
        self.add_layer_path = resource_filename("tidegates.testing", "ZOI.shp")

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
        self.known_unavailable = '3d'

    @nt.raises(RuntimeError)
    def test_unlicensed_extension(self):
        with utils.Extension(self.known_unavailable):
            pass

    def test_licensed_extension(self):
        nt.assert_equal(arcpy.CheckExtension(self.known_available), 'Available')
        with utils.Extension(self.known_available) as ext:
            nt.assert_equal(ext, 'CheckedOut')

        nt.assert_equal(arcpy.CheckExtension(self.known_available), 'Available')

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

        self.rasterfile1 = resource_filename("tidegates.testing", 'test_raster1')
        self.rasterfile2 = resource_filename("tidegates.testing", 'test_raster2')
        self.rasterfile3 = resource_filename("tidegates.testing", 'test_raster3')

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
    template_file = resource_filename("tidegates.testing", 'test_raster2')
    template = arcpy.Raster(template_file)
    array = numpy.arange(5, 25).reshape(4, 5).astype(float)

    raster = utils.array_to_raster(array, template)
    nt.assert_true(isinstance(raster, arcpy.Raster))
    nt.assert_true(raster.extent.equals(template.extent))
    nt.assert_equal(raster.meanCellWidth, template.meanCellWidth)
    nt.assert_equal(raster.meanCellHeight, template.meanCellHeight)


class Test_load_data(object):
    rasterpath = resource_filename("tidegates.testing", 'test_dem.tif')
    vectorpath = resource_filename("tidegates.testing", 'test_wetlands.shp')

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


class _process_polygons_mixin(object):
    testfile = resource_filename("tidegates.testing", "test_zones.shp")
    known_values = numpy.array([-999, 16, 150])

    def test_process(self):
        raster, res = utils.process_polygons(self.testfile, "GeoID", **self.kwargs)
        nt.assert_true(isinstance(raster, arcpy.Raster))
        nt.assert_true(isinstance(res, arcpy.Result))

        array = utils.rasters_to_arrays(raster, squeeze=True)
        arcpy.management.Delete(raster)

        flat_arr = array.flatten()
        bins = numpy.bincount(flat_arr[flat_arr > 0])
        nptest.assert_array_almost_equal(numpy.unique(array), self.known_values)
        nptest.assert_array_almost_equal(bins[bins > 0], self.known_counts)
        nt.assert_tuple_equal(array.shape, self.known_shape)


class Test_process_polygons_default(_process_polygons_mixin):
    def setup(self):
        self.kwargs = {}
        self.known_shape = (854, 661)
        self.known_counts = numpy.array([95274, 36674])


class Test_process_polygons_x02(_process_polygons_mixin):
    def setup(self):
        self.kwargs = {'cellsize': 2}
        self.known_shape = (1709, 1322)
        self.known_counts = numpy.array([381211, 146710])

class Test_process_polygons_x08(_process_polygons_mixin):
    def setup(self):
        self.kwargs = {'cellsize': 8}
        self.known_shape = (427, 330)
        self.known_counts = numpy.array([23828,  9172])

    def test_actual_arrays(self):
        known_raster_file = resource_filename("tidegates.testing", "test_zones_raster.tif")
        known_raster = utils.load_data(known_raster_file, 'raster')
        raster, result = utils.process_polygons(self.testfile, "GeoID", **self.kwargs)
        arrays = utils.rasters_to_arrays(raster, known_raster)
        arcpy.management.Delete(raster)

        nptest.assert_array_almost_equal(*arrays)


class Test_process_polygons_x16(_process_polygons_mixin):
    def setup(self):
        self.kwargs = {'cellsize': 16}
        self.known_shape = (214, 165)
        self.known_counts = numpy.array([5953, 2288])


def test_clip_dem_to_zones():
    demfile = resource_filename("tidegates.testing", 'test_dem.tif')
    zonefile = resource_filename("tidegates.testing", "test_zones_raster_small.tif")
    raster, result = utils.clip_dem_to_zones(demfile, zonefile)

    zone_r = utils.load_data(zonefile, 'raster')

    arrays = utils.rasters_to_arrays(raster, zone_r)

    dem_a, zone_a = arrays[0], arrays[1]
    arcpy.management.Delete(raster)

    nt.assert_true(isinstance(raster, arcpy.Raster))
    nt.assert_true(isinstance(result, arcpy.Result))

    known_shape = (146, 172)
    nt.assert_tuple_equal(dem_a.shape, zone_a.shape)


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

