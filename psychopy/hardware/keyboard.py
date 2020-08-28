#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""To handle input from keyboard (supercedes event.getKeys)


The Keyboard class was new in PsychoPy 3.1 and replaces the older
`event.getKeys()` calls.

Psychtoolbox versus event.getKeys
------------------------------------

On 64 bits Python3 installations it provides access to the
`Psychtoolbox kbQueue <http://psychtoolbox.org/docs/KbQueueCreate>`_ series of
functions using the same compiled C code (available in python-psychtoolbox lib).

On 32 bit installations and Python2 it reverts to the older
:func:`psychopy.event.getKeys` calls.

The new calls have several advantages:

- the polling is performed and timestamped asynchronously with the main thread
  so that times relate to when the key was pressed, not when the call was made
- the polling is direct to the USB HID library in C, which is faster than
  waiting for the operating system to poll and interpret those same packets
- we also detect the KeyUp events and therefore provide the option of returning
  keypress duration
- on Linux and Mac you can also distinguish between different keyboard devices
  (see :func:`getKeyboards`)

This library makes use, where possible of the same low-level asynchronous
hardware polling as in `Psychtoolbox <http://psychtoolbox.org/>`_

.. currentmodule:: psychopy.hardware.keyboard

Example usage

------------------------------------

.. code-block:: python

    from psychopy.hardware import keyboard
    from psychopy import core

    kb = keyboard.Keyboard()

    # during your trial
    kb.clock.reset()  # when you want to start the timer from
    keys = kb.getKeys(['right', 'left', 'quit'], waitRelease=True)
    if 'quit' in keys:
        core.quit()
    for key in keys:
        print(key.name, key.rt, key.duration)

"""

# Part of the PsychoPy library
# Copyright (C) 2002-2018 Jonathan Peirce (C) 2019-2020 Open Science Tools Ltd.
# Distributed under the terms of the GNU General Public License (GPL).

# 01/2011 modified by Dave Britton to get mouse event timing

from __future__ import absolute_import, division, print_function

from collections import deque
import sys
import copy

import psychopy.core
import psychopy.clock
from psychopy import logging
from psychopy.constants import NOT_STARTED

try:
    import psychtoolbox as ptb
    from psychtoolbox import hid
    havePTB = True
except ImportError as err:
    logging.warning(("Import Error: "
                     + err.args[0]
                     + ". Using event module for keyboard component."))
    from psychopy import event
    havePTB = False

defaultBufferSize = 10000


def getKeyboards():
    """Get info about the available keyboards.

    Only really useful on Mac/Linux because on these the info can be used to
    select a particular physical device when calling :class:`Keyboard`. On Win
    this function does return information correctly but the :class:Keyboard
    can't make use of it.

    Returns
    ----------
    A list of dicts
        USB Info including with name, manufacturer, id, etc for each device

    """
    indices, names, keyboards = hid.get_keyboard_indices()
    return keyboards


class Keyboard:
    """The Keyboard class provides access to the Psychtoolbox KbQueue-based
    calls on **Python3 64-bit** with fall-back to `event.getKeys` on legacy
    systems.

    """

    def __init__(self, device=-1, bufferSize=10000, waitForStart=False,
                 clock=None):
        """Create the device (default keyboard or select one)

        Parameters
        ----------
        device: int or dict

            On Linux/Mac this can be a device index
            or a dict containing the device info (as from :func:`getKeyboards`)
            or -1 for all devices acting as a unified Keyboard

        bufferSize: int

            How many keys to store in the buffer (before dropping older ones)

        waitForStart: bool (default False)

            Normally we'll start polling the Keyboard at all times but you
            could choose not to do that and start/stop manually instead by
            setting this to True

        """
        self.status = NOT_STARTED
        # Initiate containers for storing responses
        self.keys = []  # the key(s) pressed
        self.corr = 0  # was the resp correct this trial? (0=no, 1=yes)
        self.rt = []  # response time(s)
        self.time = []  # Epoch

        if clock:
            self.clock = clock
        else:
            self.clock = psychopy.clock.Clock()

        if havePTB:
            # get the necessary keyboard buffer(s)
            if sys.platform=='win32':
                self._ids = [-1]  # no indexing possible so get the combo keyboard
            else:
                allInds, allNames, allKBs = hid.get_keyboard_indices()
                if device==-1:
                    self._ids = allInds
                elif type(device) in [list, tuple]:
                    self._ids = device
                else:
                    self._ids = [device]

            self._buffers = {}
            self._devs = {}
            for devId in self._ids:
                # now we have a list of device IDs to monitor
                if devId==-1 or devId in allInds:
                    buffer = _keyBuffers.getBuffer(devId, bufferSize)
                    self._buffers[devId] = buffer
                    self._devs[devId] = buffer.dev

            if not waitForStart:
                self.start()

    def start(self):
        """Start recording from this keyboard """
        for buffer in self._buffers.values():
            buffer.start()

    def stop(self):
        """Start recording from this keyboard"""
        logging.warning("Stopping key buffers but this could be dangerous if"
                        "other keyboards rely on the same.")
        for buffer in self._buffers.values():
            buffer.stop()

    def getKeys(self, keyList=None, waitRelease=True, clear=True):
        """

        Parameters
        ----------
        keyList: list (or other iterable)

            The keys that you want to listen out for. e.g. ['left', 'right', 'q']

        waitRelease: bool (default True)

            If True then we won't report any "incomplete" keypress but all
            presses will then be given a `duration`. If False then all
            keys will be presses will be returned, but only those with a
            corresponding release will contain a `duration` value (others will
            have `duration=None`

        clear: bool (default True)

            If False then keep the keypresses for further calls (leave the
            buffer untouched)

        Returns
        -------
        A list of :class:`Keypress` objects

        """
        keys = []
        if havePTB:
            for buffer in self._buffers.values():
                for origKey in buffer.getKeys(keyList, waitRelease, clear):
                    # calculate rt from time and self.timer
                    thisKey = copy.copy(origKey)  # don't alter the original
                    thisKey.rt = thisKey.tDown - self.clock.getLastResetTime()
                    keys.append(thisKey)
        else:
            name = event.getKeys(keyList, modifiers=False, timeStamped=False)
            rt = self.clock.getTime()
            if len(name):
                thisKey = KeyPress(code=None, tDown=rt, name=name[0])
                keys.append(thisKey)
        return keys

    def waitKeys(maxWait=None, keyList=None, waitRelease=True, clear=True):
        keys = []
        raise NotImplementedError

    def clearEvents(self, eventType=None):
        """"""
        if havePTB:
            for buffer in self._buffers.values():
                buffer.flush()  # flush the device events to the soft buffer
                buffer._evts.clear()
                buffer._keys.clear()
                buffer._keysStillDown.clear()
        else:
            event.clearEvents(eventType)

class KeyPress(object):
    """Class to store key presses, as returned by `Keyboard.getKeys()`

    Unlike keypresses from the old event.getKeys() which returned a list of
    strings (the names of the keys) we now return several attributes for each
    key:

        .name: the name as a string (matching the previous pyglet name)
        .rt: the reaction time (relative to last clock reset)
        .tDown: the time the key went down in absolute time
        .duration: the duration of the keypress (or None if not released)

    Although the keypresses are a class they will test `==`, `!=` and `in`
    based on their name. So you can still do::

        kb = KeyBoard()
        # wait for keypresses here
        keys = kb.getKeys()
        for thisKey in keys:
            if thisKey=='q':  # it is equivalent to the string 'q'
                core.quit()
            else:
                print(thisKey.name, thisKey.tDown, thisKey.rt)
    """

    def __init__(self, code, tDown, name=None):
        self.code = code

        if name is not None:  # we have event.getKeys()
            self.name = name
            self.rt = tDown
        else:
            if code not in keyNames:
                self.name = 'n/a'
                logging.warning("Got keycode {} but that code isn't yet known")
            else:
                self.name = keyNames[code]
            if code not in keyNames:
                logging.warning('Keypress was given unknown key code ({})'.format(code))
                self.name = 'unknown'
            else:
                self.name = keyNames[code]
            self.rt = None  # can only be assigned by the keyboard object on return
        self.tDown = tDown
        self.duration = None

    def __eq__(self, other):
        return self.name == other

    def __ne__(self, other):
        return self.name != other


class _KeyBuffers(dict):
    """This ensures there is only one virtual buffer per physical keyboard.

    There is an option to get_event() from PTB without clearing but right
    now we are clearing when we poll so we need to make sure we have a single
    virtual buffer."""

    def getBuffer(self, kb_id, bufferSize=defaultBufferSize):
        if kb_id not in self:
            try:
                self[kb_id] = _KeyBuffer(bufferSize=bufferSize,
                                         kb_id=kb_id)
            except FileNotFoundError as e:
                if sys.platform == 'darwin':
                    # this is caused by a problem with SysPrefs
                    raise OSError("Failed to connect to Keyboard globally. "
                                  "You need to add PsychoPy App bundle (or the "
                                  "terminal if you run from terminal) to the "
                                  "System Preferences/Privacy/Accessibility "
                                  "(macOS <= 10.14) or "
                                  "System Preferences/Privacy/InputMonitoring "
                                  "(macOS >= 10.15).")
                else:
                    raise(e)

        return self[kb_id]


class _KeyBuffer(object):
    """This is our own local buffer of events with more control over clearing.

    The user shouldn't use this directly. It is fetched from the _keybuffers

    It stores events from a single physical device

    It's built on a collections.deque which is like a more efficient list
    that also supports a max length
    """

    def __init__(self, bufferSize, kb_id):
        self.bufferSize = bufferSize
        self._evts = deque()

        # create the PTB keyboard object and corresponding queue
        allInds, names, keyboards = hid.get_keyboard_indices()

        self._keys = []
        self._keysStillDown = []

        if kb_id == -1:
            self.dev = hid.Keyboard()  # a PTB keyboard object
        else:
            self.dev = hid.Keyboard(kb_id)  # a PTB keyboard object
        self.dev._create_queue(bufferSize)

    def flush(self):
        """Flushes and processes events from the device to this software buffer
        """
        self._processEvts()

    def _flushEvts(self):
        ptb.WaitSecs('YieldSecs', 0.00001)
        while self.dev.flush():
            evt, remaining = self.dev.queue_get_event()
            key = {}
            key['keycode'] = int(evt['Keycode'])
            key['down'] = bool(evt['Pressed'])
            key['time'] = evt['Time']
            self._evts.append(key)

    def getKeys(self, keyList=[], waitRelease=True, clear=True):
        """Return the KeyPress objects from the software buffer

        Parameters
        ----------
        keyList : list of key(name)s of interest
        waitRelease : if True then only process keys that are also released
        clear : clear any keys (that have been returned in this call)

        Returns
        -------
        A deque (like a list) of keys
        """
        self._processEvts()
        # if no conditions then no need to loop through
        if not keyList and not waitRelease:
            keyPresses = deque(self._keys)
            if clear:
                self._keys = deque()
                self._keysStillDown = deque()
            return keyPresses

        # otherwise loop through and check each key
        keyPresses = deque()
        for keyPress in self._keys:
            if waitRelease and not keyPress.duration:
                continue
            if keyList and keyPress.name not in keyList:
                continue
            keyPresses.append(keyPress)

        # clear keys in a second step (not during iteration)
        if clear:
            for key in keyPresses:
                self._keys.remove(key)

        return keyPresses

    def _clearEvents(self):
        self._evts.clear()

    def start(self):
        self.dev.queue_start()

    def stop(self):
        self.dev.queue_stop()

    def _processEvts(self):
        """Take a list of events and convert to a list of keyPresses with
        tDown and duration"""
        self._flushEvts()
        evts = deque(self._evts)
        self._clearEvents()
        for evt in evts:
            if evt['down']:
                newKey = KeyPress(code=evt['keycode'], tDown=evt['time'])
                self._keys.append(newKey)
                self._keysStillDown.append(newKey)
            else:
                for key in self._keysStillDown:
                    if key.code == evt['keycode']:
                        key.duration = evt['time'] - key.tDown
                        self._keysStillDown.remove(key)
                        break  # this key is done
                    else:
                        # we found a key that was first pressed before reading
                        pass


_keyBuffers = _KeyBuffers()

keyNamesWin = {
    49: '1', 50: '2', 51: '3', 52: '4', 53: '5',
    54: '6', 55: '7', 56: '8', 57: '9', 48: '0',
    65: 'a', 66: 'b', 67: 'c', 68: 'd', 69: 'e', 70: 'f',
    71: 'g', 72: 'h', 73: 'i', 74: 'j', 75: 'k', 76: 'l',
    77: 'm', 78: 'n', 79: 'o', 80: 'p', 81: 'q', 82: 'r',
    83: 's', 84: 't', 85: 'u', 86: 'v', 87: 'w', 88: 'x',
    89: 'y', 90: 'z',
    97: 'num_1', 98: 'num_2', 99: 'num_3',
    100: 'num_4', 101: 'num_5', 102: 'num_6', 103: 'num_7',
    104: 'num_8', 105: 'num_9', 96: 'num_0',
    112: 'f1', 113: 'f2', 114: 'f3', 115: 'f4', 116: 'f5',
    117: 'f6', 118: 'f7', 119: 'f8', 120: 'f9', 121: 'f10',
    122: 'f11', 123: 'f12',
    145: 'scrolllock', 19: 'pause', 36: 'home', 35: 'end',
    45: 'insert', 33: 'pageup', 46: 'delete', 34: 'pagedown',
    37: 'left', 40: 'down', 38: 'up', 39: 'right', 27: 'escape',
    144: 'numlock', 111: 'num_divide', 106: 'num_multiply',
    8: 'backspace', 109: 'num_subtract', 107: 'num_add',
    13: 'return', 222: 'pound', 161: 'lshift', 163: 'rctrl',
    92: 'rwindows', 32: 'space', 164: 'lalt', 165: 'ralt',
    91: 'lwindows', 93: 'menu', 162: 'lctrl', 160: 'lshift',
    20: 'capslock', 9: 'tab', 223: 'quoteleft', 220: 'backslash',
    188: 'comma', 190: 'period', 191: 'slash', 186: 'semicolon',
    192: 'apostrophe', 219: 'bracketleft', 221: 'bracketright',
    189: 'minus', 187: 'equal'
}

keyNamesMac = {
    4: 'a', 5: 'b', 6: 'c', 7: 'd', 8: 'e', 9: 'f', 10: 'g', 11: 'h', 12: 'i',
    13: 'j', 14: 'k', 15: 'l', 16: 'm', 17: 'n', 18: 'o', 19: 'p', 20: 'q',
    21: 'r', 22: 's', 23: 't', 24: 'u', 25: 'v', 26: 'w', 27: 'x', 28: 'y',
    29: 'z',
    30: '1', 31: '2', 32: '3', 33: '4', 34: '5', 35: '6', 36: '7',
    37: '8', 38: '9', 39: '0',
    40: 'return', 41: 'escape', 42: 'backspace', 43: 'tab', 44: 'space',
    45: 'minus', 46: 'equal',
    47: 'bracketleft', 48: 'bracketright', 49: 'backslash', 51: 'semicolon',
    52: 'apostrophe', 53: 'grave', 54: 'comma', 55: 'period', 56: 'slash',
    57: 'lshift',
    58: 'f1', 59: 'f2', 60: 'f3', 61: 'f4', 62: 'f5', 63: 'f6', 64: 'f7',
    65: 'f8', 66: 'f9', 67: 'f10', 68: 'f11', 69: 'f12',
    104: 'f13', 105: 'f14', 106: 'f15',
    107: 'f16', 108: 'f17', 109: 'f18', 110: 'f19',
    79: 'right', 80: 'left', 81: 'down', 82: 'up',
    224: 'lctrl', 225: 'lshift', 226: 'loption', 227: 'lcommand',
    100: 'function', 229: 'rshift', 230: 'roption', 231: 'rcommand',
    83: 'numlock', 103: 'num_equal', 84: 'num_divide', 85: 'num_multiply',
    86: 'num_subtract', 87: 'num_add', 88: 'num_enter', 99: 'num_decimal',
    98: 'num_0', 89: 'num_1', 90: 'num_2', 91: 'num_3', 92: 'num_4',
    93: 'num_5', 94: 'num_6', 95: 'num_7', 96: 'num_8', 97: 'num_9',
    74: 'home', 75: 'pageup', 76: 'delete', 77: 'end', 78: 'pagedown',
}

keyNamesLinux={
    66: 'space', 68: 'f1', 69: 'f2', 70: 'f3', 71: 'f4', 72: 'f5',
    73: 'f6', 74: 'f7', 75: 'f8', 76: 'f9', 77: 'f10', 96: 'f11', 97: 'f12',
    79: 'scrolllock', 153: 'scrolllock', 128: 'pause', 119: 'insert', 111: 'home',
    120: 'delete', 116: 'end', 113: 'pageup', 118: 'pagedown', 136: 'menu', 112: 'up',
    114: 'left', 117: 'down', 115: 'right', 50: 'quoteleft',
    11: '1', 12: '2', 13: '3', 14: '4', 15: '5', 16: '6', 17: '7', 18: '8', 19: '9', 20: '0',
    21: 'minus', 22: 'equal', 23: 'backspace', 24: 'tab', 25: 'q', 26: 'w', 27: 'e', 28: 'r',
    29: 't', 30: 'y', 31: 'u', 32: 'i', 33: 'o', 34: 'p', 35: 'bracketleft', 36: 'bracketright',
    37: 'return', 67: 'capslock', 39: 'a', 40: 's', 41: 'd', 42: 'f', 43: 'g', 44: 'h', 45: 'j',
    46: 'k', 47: 'l', 48: 'semicolon', 49: 'apostrophe', 52: 'backslash', 51: 'lshift',
    95: 'less', 53: 'z', 54: 'x', 55: 'c', 56: 'v', 57: 'b', 58: 'n', 59: 'm',
    60: 'comma', 61: 'period', 62: 'slash', 63: 'rshift', 38: 'lctrl', 65: 'lalt',
    109: 'ralt', 106: 'rctrl', 78: 'numlock', 107: 'num_divide', 64: 'num_multiply',
    83: 'num_subtract', 80: 'num_7', 81: 'num_8', 82: 'num_9', 87: 'num_add', 84: 'num_4',
    85: 'num_5', 86: 'num_6', 88: 'num_1', 89: 'num_2', 90: 'num_3',
    105: 'num_enter', 91: 'num_0', 92: 'num_decimal', 10: 'escape'
    }


if sys.platform == 'darwin':
    keyNames = keyNamesMac
elif sys.platform == 'win32':
    keyNames = keyNamesWin
else:
    keyNames = keyNamesLinux

# check if mac prefs are working
macPrefsBad = False
if sys.platform == 'darwin' and havePTB:
    try:
        Keyboard()
    except OSError:
        macPrefsBad = True
        havePTB = False
