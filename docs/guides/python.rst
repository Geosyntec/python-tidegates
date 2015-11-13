.. _python:

Using **python-tidegates** from python
======================================

You don't have to start an ArcGIS session to use *python-tidegates**.
The analytical guts of the library are completely isolated from the ArcGIS interface portions.
This allows users to directly use the analytical capabilities from a python script or an interactive python session.

There are two interfaces to the analytic capabilities:

   1. :ref:`toolbox_guide`
   2. :ref:`tidegates_guide`


Common elements of examples
---------------------------
The following import statements are prerequisites for all of the code snippets below.

.. code-block:: python

   import numpy
   import arcpy
   import tidegates
   from tidegates import utils


.. _toolbox_guide:

The ``toolbox`` API
--------------------------------

For a full description of the API, see the :mod:`tidegates.toolbox`.

The :mod:`tidegates.toolbox` interface provides a very high-level interface to **python-tidgeates** that very closely mimics the :ref:`arcgis`.
Just like how there are two form in the ArcGIS toolbox, there are two analagous classes avialable in the :mod:`tidegates.toolbox` API.

The ``Flooder`` class allows the user to estimate the extent and impact of flooding at custom elevations.

The ``StandardScenarios`` class automatically estimates the extent and impact of flooding for all combinates of the four storm surge events and sea level rise in 1-ft increments up to 6 feet.

Both classes are instantiated without any arguments and have identical ``main_execute`` methods to evaluate their scenarios.
The only difference is that ``Flooder`` requires values for the flood elevations.

Common input parameters
~~~~~~~~~~~~~~~~~~~~~~~

The following are the parameters shared by both classes.
All parameters are required except where noted.

workspace
    This is the folder or geodatabase that contains all of the input for the analysis.

    .. note: All of the input for the analysis (see below) *must* be in this workspace.

dem
    This is the raster dataset that contains the gridded topographic and bathymetric data that will be used to determine the extent of flooding.
    The original geodatabases provided contain DEMs: one at 4-m, and a second at 8-m resolution.
    The finer resolution DEM provides more detailed output, however it also requires more runtime and the analysis requires more computational resources.
    If the tool runs into a ``MemoryError`` during an analysis, try using the lower resolution raster.
    If these errors persist, Other things to try include limiting the number of **zones** analyzed or reducing the resolution of the raster even further.

    .. note: The elevations of the DEMs provided in the standard geodatabase are measured in meters.
             However, care is taken to convert the properly convert the user input into meters to match the DEM when determining the extent of flooding.

zones
    This is a polygon layer found in *workspace* that delineates the zone of influence of each tidegate.
    The original geodatabases provided include a dataset called "ZOI" that incclude this information.

ID_column
    This is the name of the field in the **zones** parameter that contains the unique idenifier of each tidegate.
    When using the "ZOI" layers provided in the geodatabases, this should be set to "GeoID".

flood_output
    This is the filename to which the extent of flooding will be saved withing **workspace**.

    .. warning: Both toolboxes will overwrite any previous output if duplicate filenames are provided.

wetlands, optional
    This is a polygon layer found within **workspace** that delineates wetlands within a study area.
    If provided, the area of wetlands inundated during each flood scenario will be added to the **flood_output** layer.

wetlands_output, optional
    This is the filename of the layer created by computing the intersections of **flood_output** and **wetlands**.
    The result is a shapefile/feature class that contains only the inundated areas of the wetlands.
    If **wetlands_output** is not provided, the information is not saved to disk.

    .. warning: Both toolboxes will overwrite any previous output if duplicate filenames are provided.

buildings, optional
    This is a polygon layer of the building footprints in the study area.
    If provided the *number* of impacted buildings will be added to each record of **flood_output**.

building_output, optional
    This is the filename of an output layer that contains all of the impacted buildings for each flood scenario.
    If **building_output** is not provided, the information is not saved to disk.

    .. warning: Both toolboxes will overwrite any previous output if duplicate filenames are provided.

Custom elevations
~~~~~~~~~~~~~~~~~
The ``Flooder`` class allows the user to input multiple elevations to be analyzed.
Thus, it has an ``elevation`` parameter not used by the ``StandardScenarios`` class.
In keeping with the formatted definitions below:

elevation
    A series of multiple custom flood elevations (in feet MSL) to be analyzed.

Code examples
~~~~~~~~~~~~~

Below is an example of using the ``Flooder`` class to evaluate custom flood elevations.

.. code-block:: python

    # define the workspace as a geodatabase
    workspace = r'F:\phobson\Tidegates\MB_Small.gdb'

    # define the flood elevations to analyze (in feef MSL)
    elevations_feet = [4.8, 6.1, 8.9, 10.5]

    # instantiate the flooder
    custom_tool = tidegates.toolbox.Flooder()

    with utils.OverwriteState(True):  # allow overwriting of any previous output
        custom_tool.main_execute(
            workspace=workspace,
            dem='dem_x08',
            zones='ZOI',
            wetlands='wetlands',
            buildings='buildings',
            ID_column='GeoID',
            flood_output='Custom_floods',
            building_output='Custom_floods_bldg',
            wetland_output='Custom_floods_wetland',
            elevations=elevations_feet
        )


Below is an example of using the ``StandardScenarios`` class to evaluate custom flood elevations.

.. code-block:: python

    # define the workspace as a geodatabase
    workspace = r'F:\phobson\Tidegates\MB_Small.gdb'

    # instantiate the flooder
    std_tool = tidegates.toolbox.StandardScenarios()

    with utils.OverwriteState(True):  # allow overwriting of any previous output
        std_tool.main_execute(
            workspace=workspace,
            dem='dem_x08',
            zones='ZOI',
            wetlands='wetlands',
            buildings='buildings',
            ID_column='GeoID',
            flood_output='Std_floods',
            building_output='Std_floods_bldg',
            wetland_output='Std_floods_wetland',
        )


.. _tidegates_guide:

The ``tidegate`` API
--------------------

For a full description of the API, see the :mod:`tidegates.tidegates`.

The :mod:`tidegates.tidegates` submodule contains four functions:

   1. :func:`tidegates.tidegates.flood_area`
   2. :func:`tidegates.tidegates.assess_impact`
   3. :func:`tidegates.tidegates.area_of_impacts`
   4. :func:`tidegates.tidegates.count_of_impacts`
