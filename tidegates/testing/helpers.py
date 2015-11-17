import nose.tools as nt
from numpy import errstate, hstack, array
import numpy.testing as nptest
import arcpy

from warnings import simplefilter
import sys
import os

try:
    import fiona
    has_fiona = True
except ImportError:
    fiona = None
    has_fiona = False

# Check for availability of ArcGIS Spatial Analyst (required to run certain tests)
if arcpy.CheckExtension("Spatial") == u'Available':
    has_spatial = True
else:
    has_spatial = False

def assert_shapefiles_are_close(baselinefile, outputfile, atol=0.001, ngeom=5):
    with fiona.open(outputfile, 'r') as result:
        result_records = list(result)

    with fiona.open(baselinefile, 'r') as baseline:
        known_records = list(baseline)

    for rr, kr in zip(result_records, known_records):
        nt.assert_dict_equal(rr['properties'], kr['properties'])
        nt.assert_equal(rr['geometry']['type'], kr['geometry']['type'])
        nt.assert_equal(len(rr['geometry']['coordinates']), len(kr['geometry']['coordinates']))

        _ngeom = min(len(rr['geometry']['coordinates']), ngeom)
        nptest.assert_allclose(
            hstack([array(r) for r in rr['geometry']['coordinates'][:_ngeom]]),
            hstack([array(k) for k in kr['geometry']['coordinates'][:_ngeom]]),
            atol=atol
        )


def _show_package_info(package, name):
    if name == 'arcpy':
        version = package.GetInstallInfo()['Version']
        packagedir = package.GetInstallInfo()['SourceDir']
    else:
        version = package.__version__
        packagedir = os.path.dirname(package.__file__)

    print("%s version %s is installed in %s" % (name, version, packagedir))


def _show_system_info():
    import nose
    import arcpy
    import numpy

    pyversion = sys.version.replace('\n','')
    print("Python version %s" % pyversion)
    print("nose version %d.%d.%d" % nose.__versioninfo__)

    _show_package_info(arcpy, 'arcpy')

    _show_package_info(numpy, 'numpy')

    if has_fiona:
        _show_package_info(fiona, 'fiona')
    else:
        print("fiona not installed")


class NoseWrapper(nptest.Tester):
    '''
    This is simply a monkey patch for numpy.testing.Tester.
    It allows extra_argv to be changed from its default None to ['--exe'] so
    that the tests can be run the same across platforms.  It also takes kwargs
    that are passed to numpy.errstate to suppress floating point warnings.
    '''


    def test(self, label='fast', verbose=1, with_id=True, exe=True,
             doctests=False, coverage=False, packageinfo=True, extra_argv=None,
             **kwargs):
        '''
        Run tests for module using nose
        %(test_header)s
        doctests : boolean
            If True, run doctests in module, default False
        coverage : boolean
            If True, report coverage of NumPy code, default False
            (Requires the coverage module:
             http://nedbatchelder.com/code/modules/coverage.html)
        kwargs
            Passed to numpy.errstate.  See its documentation for details.
        '''
        if extra_argv is None:
            extra_argv = []

        if with_id:
            extra_argv.extend(['--with-id'])

        if exe:
            extra_argv.extend(['--exe'])

        # cap verbosity at 3 because nose becomes *very* verbose beyond that
        verbose = min(verbose, 3)
        nptest.utils.verbose = verbose

        if packageinfo:
            _show_system_info()

        if doctests:
            print("\nRunning unit tests and doctests for %s" % self.package_name)
        else:
            print("\nRunning unit tests for %s" % self.package_name)

        # reset doctest state on every run
        import doctest
        doctest.master = None

        argv, plugins = self.prepare_test_args(label, verbose, extra_argv,
                                               doctests, coverage)

        # with catch_warnings():
        with errstate(**kwargs):
            simplefilter('ignore', category=DeprecationWarning)
            t = nptest.noseclasses.NumpyTestProgram(argv=argv, exit=False, plugins=plugins)
        return t.result
