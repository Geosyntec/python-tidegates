.. _install:

Installing **python-tidegates**
===============================

**python-tidegates** is an ArcGIS python toolbox and library for analyzing the extent of flooding and damage to assets under varying sea level rise and storm surge scenarios.

Terminology
-----------
ArcGIS
    The suite of proprietarty software application licensed by Esri.
    Includes the ArcMap and ArcCatalog applications.

ArcGIS session
    Use of either ArcMap or ArcCatalog.

command prompt or terminal
    The Windows interface to its command-line tools.

Python
    An open source, dynamic programming language that Esri bundles with ArcGIS.
    The current version (as of 2015-11-11) is Python 3.5.
    However ArcGIS 10 installations use Python 2.7, released 2010-07-03.

numpy
    An open source numerical extension to python that provides the basis for must scientific libraries in python.

arcpy
    A proprietary Python-based interface to some of the geoprocessing and cartographic functionality of ArcGIS.

nose
    An open source unit test runner for python.

mock
    An open source unit testing library that allows you to replace complex parts of a system and inspect how they are used.

fiona
    An open source python library for readinga and writing shapefiles.

jupyter
    An open source, programming language-agnostic suite tools aimed at facilitating reproducible scientific work.
    The name stands for "Julia", "Python", and "R", the names of three of the dominating scientific computing languages.

git
    A distributed version control software. See https://git-scm.com/ for more details.

API
  "Application programming interface". This is essentially the public, developer-faceing functions an classes of one library that a developer can used to create yet another library.



Downloading **python-tidegates**
--------------------------------
An always current zipped archive of the tool can be downloaded at https://github.com/Geosyntec/python-tidegates/archive/master.zip.

Alternatively, you can simply clone this repository through git:
::

    git clone https://github.com/Geosyntec/python-tidegates.git


Dependencies
------------

Runtime
~~~~~~~
This library requires the following python-packages to be installed on your system:
  1. Python 2.7
  2. arcpy
  3. numpy

Testing
~~~~~~~
To run the full suite of tests packages with this system, you additionally need:
  1. nose
  2. mock
  3. fiona (optional)

Both nose and mock can be installed via pip (e.g., `pip install mock`), however fiona can be quite tricky to install on some systems.
For that reason fiona is an optional dependency.
Tests requiring it are skipped if it is not found while the tests are running.
The nose and mock modules are absolutely required, however.

Installing **python-tidegates**
-------------------------------
This is a pure-python library, so installation from source (even on Windows) is not an issue.
After acquiring and unzipping the source-code in some fashion, open a terminal, navigate into the directory, and execute

::

    pip install .

(The ``.`` tells the command that the package is in the current directory)

Inside a fresh, new terminal, that looks like this:

::

    Microsoft Windows [Version 6.3.9600]
    (c) 2013 Microsoft Corporation. All rights reserved.

    C:\Users\phobson> cd C:\Users\phobson\Downloads\python-tidegates-master

    C:\Users\phobson\Downloads\python-tidegates-master> pip install .
    Processing c:\users\phobson\downloads\python-tidegates-master
    Building wheels for collected packages: tidegates
      Running setup.py bdist_wheel for tidegates
      Stored in directory: C:\Users\phobson\AppData\Local\pip\Cache\wheels\bc\1d\a3\fae5dffd5c5863...
    Successfully built tidegates
    Installing collected packages: tidegates
    Successfully installed tidegates-0.1

At that point, **python-tidegates** as been installed.


Running the test suite
----------------------
The code base that powers the GIS toolboxes uses a code QC technique known as `unit testing`_.
In this case, we rely on the python package `_nose` to find, collect, and execute all of the tests.

.. _unit testing: https://en.wikipedia.org/wiki/Unit_testing
.. _nose: https://nose.readthedocs.org/en/latest/

With all of the required testing dependencies installed, navigate to the source directory and execute the ``nosetests`` command.
That entire process looks something like this.

::

  Microsoft Windows [Version 6.3.9600]
  (c) 2013 Microsoft Corporation. All rights reserved.

  C:\Users\phobson> cd C:\Users\phobson\Downloads\python-tidegates-master

  C:\Users\phobson\Downloads\python-tidegates-master> nosetests
  ........................................
  ----------------------------------------------------------------------
  Ran 40 tests in 5.634s

Depending on your system, more tests may be executed, and some might by skipped.
