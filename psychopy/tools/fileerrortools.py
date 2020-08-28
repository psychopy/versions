#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Part of the PsychoPy library
# Copyright (C) 2002-2018 Jonathan Peirce (C) 2019-2020 Open Science Tools Ltd.
# Distributed under the terms of the GNU General Public License (GPL).

"""Functions and classes related to file and directory error handling
"""
from __future__ import absolute_import, print_function

from builtins import str
import os
import glob

from psychopy import logging


def handleFileCollision(fileName, fileCollisionMethod):
    """Handle filename collisions by overwriting, renaming, or failing hard.

    :Parameters:

        fileCollisionMethod: 'overwrite', 'rename', 'fail'
            If a file with the requested name already exists, specify
            how to deal with it. 'overwrite' will overwite existing
            files in place, 'rename' will append an integer to create
            a new file ('trials1.psydat', 'trials2.pysdat' etc) and
            'error' will raise an IOError.
    """
    if fileCollisionMethod == 'overwrite':
        logging.warning('Data file, %s, will be overwritten' % fileName)
    elif fileCollisionMethod == 'fail':
        msg = ("Data file %s already exists. Set argument "
               "fileCollisionMethod to overwrite.")
        raise IOError(msg % fileName)
    elif fileCollisionMethod == 'rename':
        rootName, extension = os.path.splitext(fileName)
        matchingFiles = glob.glob("%s*%s" % (rootName, extension))

        # Build the renamed string.
        if not matchingFiles:
            fileName = "%s%s" % (rootName, extension)
        else:
            fileName = "%s_%d%s" % (rootName, len(matchingFiles), extension)

        # Check to make sure the new fileName hasn't been taken too.
        if os.path.exists(fileName):
            msg = ("New fileName %s has already been taken. Something "
                   "is wrong with the append counter.")
            raise IOError(msg % fileName)

    else:
        msg = "Argument fileCollisionMethod was invalid: %s"
        raise ValueError(msg % str(fileCollisionMethod))

    return fileName
