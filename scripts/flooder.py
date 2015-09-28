import os
import sys
import glob
import datetime

import numpy

import arcpy

import tidegates

if __name__ == '__main__':
    # input from dialogue
    with tidegates.utils.WorkSpace(sys.argv[1]) as ws:
        outputlayers = tidegates.flood_area(*sys.argv[2:])

    mapdoc = tidegates.units.EasyMapDoc("CURRENT")
    for lyr in outputlayers:
        mapdoc.add_layer(lyr)
