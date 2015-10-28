# python-tidegates
An ArcGIS python toolbox and library for analyzing extent of flooding and damage to assets under varying sea level rise and storm surge scenarios.

## Terminology
  1. ArcGIS: the suite of proprietarty software application licensed by Esri. Includes the ArcMap and ArcCatalog applications.
  1. ArcGIS session: use of either ArcMap or ArcCatalog.
  1. prompt or terminal: the Windows interface to its command-line tools.
  1. Python: an open source, dynamic programming language that Esri bundles with ArcGIS.
  1. numpy: an open source numerical extension to python that provides the basis for must scientific libraries in python.
  1. arcpy: a proprietary Python-based interface to some of the geoprocessing functionality of ArcGIS.
  1. nose: an open source unit test runner for python.
  1. juptyer: an open source, programming language-agnostic suite tools aimed at facilitating reproducible scientific work.
     The name stands for "Julia", "Python", and "R", the names of three of the dominating scientific computing languages.


## Download
An always current zipped archive of the tool can be [downloaded here](https://github.com/Geosyntec/python-tidegates/archive/master.zip).
Alternatively, you can simply clone this repository through git:

```
git clone https://github.com/Geosyntec/python-tidegates.git
```

## Dependencies
This library requires the following python-packages to be installed on your system:
  1. Python 2.7
  1. arcpy
  1. numpy
  
All of these are bundled with modern ArcGIS installations. 
Additional libraries are required to run the test suite.
See the section titled **Running the test suite** for more information.

## Installation and use
This is a pure-python library, so installation from source -- even on Windows --is not an issue.
After acquiring and unzipping the source-code in some fashion, open a command window, navigate into the directory, and execute `pip install .`.
In total, that looks like this:

::opens new command prompt:: ...
```
Microsoft Windows [Version 6.3.9600]
(c) 2013 Microsoft Corporation. All rights reserved.

C:\Users\phobson
$ cd C:\Users\phobson\Downloads\python-tidegates-master

C:\Users\phobson\Downloads\python-tidegates-master
$ pip install .
Processing c:\users\phobson\downloads\python-tidegates-master
Building wheels for collected packages: tidegates
  Running setup.py bdist_wheel for tidegates
  Stored in directory: C:\Users\phobson\AppData\Local\pip\Cache\wheels\bc\1d\a3\fae5dffd5c58635786503464001432a9c5b8e8f5
de28171a77
Successfully built tidegates
Installing collected packages: tidegates
Successfully installed tidegates-0.1
```

## Small Sample Dataset
This repository contains a very small sample dataset that is used to:
  1. Run the test suite
  1. Provide a minimal demostration of the toolbox
  
### Running the test suite
The code base that powers the GIS toolboxes is uses a code QC technique known as [unit testing](https://en.wikipedia.org/wiki/Unit_testing).
In this case, we rely on the python package [`nose`](https://nose.readthedocs.org/en/latest/) to find, collect, and execute all of the tests.

To install `nose`, execute the following in a command window in any directory:
```
pip install nose
```

Aftwards, navigate back to the source directory and execute the `nosetests` command.
That entire process looks like this.

```
Microsoft Windows [Version 6.3.9600]
(c) 2013 Microsoft Corporation. All rights reserved.

C:\Users\phobson
$ cd C:\Users\phobson\Downloads\python-tidegates-master

C:\Users\phobson\Downloads\python-tidegates-master
$ pip install .
Processing c:\users\phobson\downloads\python-tidegates-master
nosetests
........................................
----------------------------------------------------------------------
Ran 40 tests in 5.634s
```

Each dot above represents a test that pass. 
Alternatively, you can use `nosetests --verbose` and the name descriptive of each test will be printed to the terminal.

### Using the tool
TDB

## License
Released under a BSD license. See the [LICENSE](https://github.com/Geosyntec/python-tidegates/blob/master/LICENSE) file for more informat.
