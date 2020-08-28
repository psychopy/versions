#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Load and play sounds

We have used a number of different Python libraries ("backends") for generating
sounds in PsychoPy. We started with `Pygame`, then tried `pyo` and `sounddevice`
but we now strongly recommend you use the PTB setting. That uses the
`PsychPortAudio`_ engine, written by Mario Kleiner for `Psychophysics Toolbox`_.

With the PTB backend you get some options about how agressively you want to try
for low latency, and there is also an option to pre-schedule a sound to play at
a given time in the future.

By default PsychoPy will try to use the following Libs, in this order, for
sound reproduction but you can alter the order in
preferences > hardware > audioLib:
    ['sounddevice', 'pygame', 'pyo']
For portaudio-based backends (all except for pygame) there is also a
choice of the underlying sound driver (e.g. ASIO, CoreAudio etc).

After importing sound, the sound lib and driver being used will be stored as::
    `psychopy.sound.audioLib`
    `psychopy.sound.audioDriver`

.. PTB

.. _PsychPortAudio: http://psychtoolbox.org/docs/PsychPortAudio-Open
.. _Psychophysics Toolbox: http://psychtoolbox.org
"""

# Part of the PsychoPy library
# Copyright (C) 2002-2018 Jonathan Peirce (C) 2019-2020 Open Science Tools Ltd.
# Distributed under the terms of the GNU General Public License (GPL).

from __future__ import absolute_import, division, print_function

from builtins import str
from past.types import basestring
import sys
import os
from psychopy import logging, prefs, exceptions, constants

pyoSndServer = None
Sound = None
audioLib = None
audioDriver = None
bits32 = (sys.maxsize==4294967296)

_audioLibs = ['PTB', 'sounddevice', 'pyo', 'pysoundcard', 'pygame']
failed = []

# check if this is being imported on Travis (has no audio card)
travisCI = bool(str(os.environ.get('TRAVIS')).lower() == 'true')
if travisCI:
    # for sounddevice we built in some TravisCI protection but not in pyo
    prefs.hardware['audioLib'] = ['sounddevice']

if isinstance(prefs.hardware['audioLib'], basestring):
    prefs.hardware['audioLib'] = [prefs.hardware['audioLib']]
for thisLibName in prefs.hardware['audioLib']:
    try:
        if thisLibName.lower() == 'ptb':
            from . import backend_ptb as backend
            Sound = backend.SoundPTB
            audioDriver = backend.audioDriver
        elif thisLibName == 'pyo':
            from . import backend_pyo as backend
            Sound = backend.SoundPyo
            pyoSndServer = backend.pyoSndServer
            audioDriver = backend.audioDriver
        elif thisLibName == 'sounddevice':
            from . import backend_sounddevice as backend
            Sound = backend.SoundDeviceSound
        elif thisLibName == 'pygame':
            from . import backend_pygame as backend
            Sound = backend.SoundPygame
        elif thisLibName == 'pysoundcard':
            from . import backend_pysound as backend
            Sound = backend.SoundPySoundCard
        else:
            msg = ("audioLib pref should be one of {!r}, not {!r}"
                   .format(_audioLibs, thisLibName))
            raise ValueError(msg)
        # if we got this far we were successful in loading the lib
        audioLib = thisLibName
        init = backend.init
        if hasattr(backend, 'getDevices'):
            getDevices = backend.getDevices
        logging.info('sound is using audioLib: %s' % audioLib)
        break
    except exceptions.DependencyError as e:
        failed.append(thisLibName.lower())
        msg = '%s audio lib was requested but not loaded: %s'
        logging.warning(msg % (thisLibName, sys.exc_info()[1]))
        continue  # to try next audio lib

if audioLib is None:
    raise exceptions.DependencyError(
            "No sound libs could be loaded. Tried: {}\n"
            "Check whether the necessary sound libs are installed"
            .format(prefs.hardware['audioLib']))
elif audioLib.lower() != 'ptb':
    if constants.PY3 and not bits32 and 'ptb' not in failed:  
        # Could be running PTB, just aren't?
        logging.warning("We strongly recommend you activate the PTB sound "
                        "engine in PsychoPy prefs as the preferred audio "
                        "engine. Its timing is vastly superior. Your prefs "
                        "are currently set to use {} (in that order)."
                        .format(prefs.hardware['audioLib']))
    else:  # Can't run PTB anyway due to Py2 or 32bit system
        logging.warning("For experiments that use audio stimuli, timing will "
                        "be much better if you upgrade your PsychoPy "
                        "installation to a 64bit Python3 installation and use "
                        "the PTB backend.")


# function to set the device (if current lib allows it)
def setDevice(dev, kind=None):
    """Sets the device to be used for new streams being created.

    :param dev: the device to be used (name, index or sounddevice.device)
    :param kind: one of [None, 'output', 'input']
    """
    if not hasattr(backend, 'defaultOutput'):
        raise IOError("Attempting to SetDevice (audio) but not supported by "
                      "the current audio library ({!r})".format(audioLib))
    if hasattr(dev,'name'):
        dev = dev['name']
    if kind is None:
        backend.defaultInput = backend.defaultOutput = dev
    elif kind == 'input':
        backend.defaultInput = dev
    elif kind == 'output':
        backend.defaultOutput = dev
    else:
        if travisCI:  # travisCI doesn't have any audio devices at all. Ignore
            return
        else:
            raise TypeError("`kind` should be one of [None, 'output', 'input']"
                            "not {!r}".format(kind))

# Set the device according to user prefs (if current lib allows it)
deviceNames = []
if hasattr(backend, 'defaultOutput'):
    pref = prefs.hardware['audioDevice']
    # is it a list or a simple string?
    if type(prefs.hardware['audioDevice'])==list:
        # multiple options so use zeroth
        dev = prefs.hardware['audioDevice'][0]
    else:
        # a single option
        dev = prefs.hardware['audioDevice']
    # is it simply "default" (do nothing)
    if dev=='default' or travisCI:
        pass  # do nothing
    elif dev not in backend.getDevices(kind='output'):
        deviceNames = sorted(backend.getDevices(kind='output').keys())
        logging.warn(u"Requested audio device '{}' that is not available on "
                        "this hardware. The 'audioDevice' preference should be one of "
                        "{}".format(dev, deviceNames))
    else:
        setDevice(dev, kind='output')
