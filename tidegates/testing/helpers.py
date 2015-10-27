import nose.tools as nt
from numpy import errstate
import numpy.testing as nptest

from warnings import simplefilter
import distutils
import sys
import subprocess
from pkg_resources import resource_string


def assert_shapefiles_are_close(baselinefile, outputfile, atol=0.001):
    with fiona.open(outputfile, 'r') as result:
        result_records = list(result)

    with fiona.open(baselinefile, 'r') as baseline:
        base_records = list(baseline)

    for rr, br in zip(result_records, base_records):
        nt.assert_dict_equal(rr['properties'], br['properties'])
        nt.assert_equal(rr['geometry']['type'], br['geometry']['type'])
        nptest.assert_allclose(rr['geometry']['coordinates'], br['geometry']['coordinates'], atol=atol)


def _show_package_info(package, name):
    packagedir = os.path.dirname(package.__file__)
    print("%s version %s is installed in %s" % (name, package.__version__, packagedir))


def _show_system_info():
    import nose

    pyversion = sys.version.replace('\n','')
    print("Python version %s" % pyversion)
    print("nose version %d.%d.%d" % nose.__versioninfo__)

    import arcpy
    _show_package_info(numpy, 'arcpy')

    import numpy
    _show_package_info(scipy, 'numpy')

    # import fiona
    # _show_package_info(matplotlib, 'fiona')


class NoseWrapper(nptest.Tester):
    '''
    This is simply a monkey patch for numpy.testing.Tester.
    It allows extra_argv to be changed from its default None to ['--exe'] so
    that the tests can be run the same across platforms.  It also takes kwargs
    that are passed to numpy.errstate to suppress floating point warnings.
    '''


    def test(self, label='fast', verbose=1, with_id=True, exe=True,
             doctests=False, coverage=False, packageinfo=True, extra_argv=[],
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
