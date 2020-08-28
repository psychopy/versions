#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Part of the PsychoPy library
# Copyright (C) 2002-2018 Jonathan Peirce (C) 2019-2020 Open Science Tools Ltd.
# Distributed under the terms of the GNU General Public License (GPL).

from __future__ import absolute_import, division, print_function

from builtins import range
from past.builtins import basestring
from builtins import object
import numpy
import copy
from os import path
from psychopy import logging
from psychopy.constants import (STARTED, PLAYING, PAUSED, FINISHED, STOPPED,
                                NOT_STARTED, FOREVER)
from psychopy.tools.filetools import pathToString
from sys import platform


if platform == 'win32':
    mediaLocation = "C:\\Windows\Media"
elif platform == 'darwin':
    mediaLocation = "/System/Library/Sounds/"
elif platform.startswith("linux"):
    mediaLocation = "/usr/share/sounds"

stepsFromA = {
    'C': -9, 'Csh': -8,
    'Dfl': -8, 'D': -7, 'Dsh': -6,
    'Efl': -6, 'E': -5,
    'F': -4, 'Fsh': -3,
    'Gfl': -3, 'G': -2, 'Gsh': -1,
    'Afl': -1, 'A': 0, 'Ash': +1,
    'Bfl': +1, 'B': +2, 'Bsh': +2}
knownNoteNames = sorted(stepsFromA.keys())


def apodize(soundArray, sampleRate):
    """Apply a Hanning window (5ms) to reduce a sound's 'click' onset / offset
    """
    hwSize = int(min(sampleRate // 200, len(soundArray) // 15))
    hanningWindow = numpy.hanning(2 * hwSize + 1)
    soundArray = copy.copy(soundArray)
    soundArray[:hwSize] *= hanningWindow[:hwSize]
    soundArray[-hwSize:] *= hanningWindow[hwSize + 1:]
    return soundArray


class HammingWindow(object):
    def __init__(self, winSecs, soundSecs, sampleRate):
        """

        :param winSecs:
        :param soundSecs:
        :param sampleRate:
        """
        self.sampleRate = sampleRate
        self.winSecs = winSecs
        self.winSamples = int(round(sampleRate*winSecs))
        self.soundSecs = soundSecs
        self.soundSamples = int(round(sampleRate*soundSecs))
        self.startWindow = numpy.hanning(self.winSamples*2)[0:self.winSamples]
        self.endWindow = numpy.hanning(self.winSamples*2)[self.winSamples:]
        self.finalWinStart = self.soundSamples-self.winSamples

    def nextBlock(self, t, blockSize):
        """Returns a block to be multiplied with the current sound block or 1.0

        :param t: current position in time (secs)
        :param blockSize: block size for the sound needing the hanning window
        :return: numpy array of length blockSize
        """
        startSample = int(t*self.sampleRate)
        if startSample < self.winSamples:
            # we're in beginning hanning window (start of sound)
            # 2 options:
            #  - block is fully within window
            #  - block starts in window but ends after window
            block = numpy.ones(blockSize)
            winEndII = min(self.winSamples,  # if block goes beyond hann win
                           startSample+blockSize)  # if block shorter
            blockEndII = min(self.winSamples-startSample,  # if block beyond
                             blockSize)  # if block shorter
            block[0:blockEndII] = self.startWindow[startSample:winEndII]
        elif startSample >= self.soundSamples:
            block = None  # the sound has finished (shouldn't have got here!)
        elif startSample >= self.finalWinStart-blockSize:
            # we're in final hanning window (end of sound)
            # More complicated, with 3 options:
            #  - block starts before win
            #  - start/end during win
            #  - start during but end after win
            block = numpy.ones(blockSize)  # the initial flat part
            blockStartII = max(self.finalWinStart-startSample,
                         0)  # if block start inside window
            blockEndII = min(blockSize,  # if block ends in hann win
                             self.soundSamples-startSample)  # ends after snd
            winStartII = max(0,  # current block ends in win but starts before
                             startSample-self.finalWinStart)
            winEndII = min(self.winSamples,
                           startSample+blockSize-self.finalWinStart)
            block[blockStartII:blockEndII] = \
                self.endWindow[winStartII:winEndII]
        else:
            block = None  # we're in the middle of sound so no need for window
        if block is not None:
            block.shape = [len(block), 1]
        return block

class _SoundBase(object):
    """Base class for sound object, from one of many ways.
    """
    # Must be provided by class SoundPygame or SoundPyo:
    # def __init__()
    # def play(self, fromStart=True, **kwargs):
    # def stop(self, log=True):
    # def getDuration(self):
    # def getVolume(self):
    # def setVolume(self, newVol, log=True):
    # def _setSndFromFile(self, fileName):
    # def _setSndFromArray(self, thisArray):

    def setSound(self, value, secs=0.5, octave=4, hamming=True, log=True):
        """Set the sound to be played.

        Often this is not needed by the user - it is called implicitly during
        initialisation.

        :parameters:

            value: can be a number, string or an array:
                * If it's a number between 37 and 32767 then a tone will
                  be generated at that frequency in Hz.
                * It could be a string for a note ('A', 'Bfl', 'B', 'C',
                  'Csh'. ...). Then you may want to specify which octave.
                * Or a string could represent a filename in the current
                  location, or mediaLocation, or a full path combo
                * Or by giving an Nx2 numpy array of floats (-1:1) you can
                  specify the sound yourself as a waveform

            secs: duration (only relevant if the value is a note name or
                a frequency value)

            octave: is only relevant if the value is a note name.
                Middle octave of a piano is 4. Most computers won't
                output sounds in the bottom octave (1) and the top
                octave (8) is generally painful

            hamming: boolean (default True) to indicate if the sound should
                be apodized (i.e., the onset and offset smoothly ramped up from
                down to zero). The function apodize uses a Hanning window, but
                arguments named 'hamming' are preserved so that existing code
                is not broken by the change from Hamming to Hanning internally.
                Not applied to sounds from files.
        """
        # Re-init sound to ensure bad values will raise error during setting:
        self._snd = None

        # Coerces pathlib obj to string, else returns inputted value
        value = pathToString(value)
        try:
            # could be '440' meaning 440
            value = float(value)
        except (ValueError, TypeError):
            # this is a string that can't be a number, eg, a file or note
            pass
        else:
            # we've been asked for a particular Hz
            if value < 37 or value > 20000:
                msg = 'Sound: bad requested frequency %.0f'
                raise ValueError(msg % value)
            self._setSndFromFreq(value, secs, hamming=hamming)
        if isinstance(value, basestring):
            if value.capitalize() in knownNoteNames:
                self._setSndFromNote(value.capitalize(), secs, octave,
                                     hamming=hamming)
            else:
                # try finding a file
                self.fileName = None
                for filePath in ['', mediaLocation]:
                    p = path.join(filePath, value)
                    if path.isfile(p):
                        self.fileName = p
                        break
                    elif path.isfile(p + '.wav'):
                        self.fileName = p = p + '.wav'
                        break
                if self.fileName is None:
                    msg = "setSound: could not find a sound file named "
                    raise ValueError(msg + value)
                else:
                    self._setSndFromFile(p)
        elif type(value) in [list, numpy.ndarray]:
            # create a sound from the input array/list
            self._setSndFromArray(numpy.array(value))
        # did we succeed?
        if self._snd is None:
            pass  # raise ValueError, "Could not make a "+value+" sound"
        else:
            if log and self.autoLog:
                logging.exp("Set %s sound=%s" % (self.name, value), obj=self)
            self.status = NOT_STARTED

    def _setSndFromNote(self, thisNote, secs, octave, hamming=True):
        # note name -> freq -> sound
        freqA = 440.0
        thisOctave = octave - 4
        mult = 2.0**(stepsFromA[thisNote] / 12.)
        thisFreq = freqA * mult * 2.0 ** thisOctave
        self._setSndFromFreq(thisFreq, secs, hamming=hamming)

    def _setSndFromFreq(self, thisFreq, secs, hamming=True):
        # note freq -> array -> sound
        if secs < 0:
            # want infinite duration - create 1 sec sound and loop it
            secs = 10.0
            self.loops = -1
        if not self.sampleRate:
            self.sampleRate = self._getDefaultSampleRate()
        nSamples = int(secs * self.sampleRate)
        outArr = numpy.arange(0.0, 1.0, 1.0 / nSamples)
        outArr *= 2 * numpy.pi * thisFreq * secs
        outArr = numpy.sin(outArr)
        if hamming and nSamples > 30:
            outArr = apodize(outArr, self.sampleRate)
        self._setSndFromArray(outArr)

    def _getDefaultSampleRate(self):
        """For backends this might depend on what streams are open"""
        return 44100

    def getDuration(self):
        """Return the duration of the sound"""
        return self.duration

    def getVolume(self):
        """Returns the current volume of the sound (0.0 to 1.0, inclusive)
        """
        return self.volume

    def getLoops(self):
        """Returns the current requested loops value for the sound (int)
        """
        return self.loops

    def setVolume(self, newVol, log=True):
        """Sets the current volume of the sound (0.0 to 1.0, inclusive)
        """
        self.volume = min(1.0, max(0.0, newVol))
        self.needsUpdate = True
        if log and self.autoLog:
            logging.exp("Sound %s set volume %.3f" %
                        (self.name, self.volume), obj=self)

    def setLoops(self, newLoops, log=True):
        """Sets the current requested extra loops (int)"""
        self.loops = int(newLoops)
        self.needsUpdate = True
        if log and self.autoLog:
            logging.exp("Sound %s set loops %s" %
                        (self.name, self.loops), obj=self)
