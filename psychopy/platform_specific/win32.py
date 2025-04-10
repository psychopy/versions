#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Part of the PsychoPy library
# Copyright (C) 2002-2018 Jonathan Peirce (C) 2019-2025 Open Science Tools Ltd.
# Distributed under the terms of the GNU General Public License (GPL).

# These are correct for win32, not sure about 64bit versions
# DEFINE NORMAL_PRIORITY_CLASS 32
# DEFINE IDLE_PRIORITY_CLASS 64
# DEFINE HIGH_PRIORITY_CLASS 128
# DEFINE REALTIME_PRIORITY_CLASS 1600
# define THREAD_PRIORITY_IDLE            -15
# define THREAD_PRIORITY_LOWEST          -2
# define THREAD_PRIORITY_BELOW_NORMAL    -1
# define THREAD_PRIORITY_NORMAL          0
# define THREAD_PRIORITY_ABOVE_NORMAL    1
# define THREAD_PRIORITY_HIGHEST         2
# define THREAD_PRIORITY_TIME_CRITICAL   15

try:
    from ctypes import windll
    from ctypes.wintypes import HANDLE, DWORD, BOOL, INT, UINT
    windll = windll.kernel32
    importWindllFailed = False
except Exception:
    importWindllFailed = True
    from .. import logging
    logging.debug("rush() not available because import windll "
                  "failed in psychopy/platform_specific/win32.py")

FALSE = 0

PROCESS_SET_INFORMATION = 0x0200
PROCESS_QUERY_INFORMATION = 0x0400

NORMAL_PRIORITY_CLASS = 32
HIGH_PRIORITY_CLASS = 128
REALTIME_PRIORITY_CLASS = 256
THREAD_PRIORITY_NORMAL = 0
THREAD_PRIORITY_HIGHEST = 2
THREAD_PRIORITY_TIME_CRITICAL = 15

# sleep signals
ES_CONTINUOUS = 0x80000000
ES_DISPLAY_REQUIRED = 0x00000002
ES_SYSTEM_REQUIRED = 0x00000001

GetCurrentProcessId = windll.GetCurrentProcessId
GetCurrentProcessId.restype = HANDLE

OpenProcess = windll.OpenProcess
OpenProcess.restype = HANDLE
OpenProcess.argtypes = (DWORD, BOOL, DWORD)

GetCurrentThread = windll.GetCurrentThread
GetCurrentThread.restype = HANDLE

SetPriorityClass = windll.SetPriorityClass
SetPriorityClass.restype = BOOL
SetPriorityClass.argtypes = (HANDLE, DWORD)

SetThreadPriority = windll.SetThreadPriority
SetThreadPriority.restype = BOOL
SetThreadPriority.argtypes = (HANDLE, INT)

SetThreadExecutionState = windll.SetThreadExecutionState
SetThreadExecutionState.restype = UINT
SetThreadExecutionState.argtypes = (UINT,)


def rush(enable=True, realtime=False):
    """Raise the priority of the current thread/process.

    Set with rush(True) or rush(False)

    Beware and don't take priority until after debugging your code
    and ensuring you have a way out (e.g. an escape sequence of
    keys within the display loop). Otherwise you could end up locked
    out and having to reboot!
    """
    if importWindllFailed:
        return False

    pr_rights = PROCESS_QUERY_INFORMATION | PROCESS_SET_INFORMATION
    pr = windll.OpenProcess(pr_rights, FALSE, GetCurrentProcessId())
    thr = windll.GetCurrentThread()

    # In this context, non-zero is success and zero is error
    out = 1

    if enable:
        if not realtime:
            out = SetPriorityClass(pr, HIGH_PRIORITY_CLASS) != 0
            out &= SetThreadPriority(thr, THREAD_PRIORITY_HIGHEST) != 0
        else:
            out = SetPriorityClass(pr, REALTIME_PRIORITY_CLASS) != 0
            out &= SetThreadPriority(thr, THREAD_PRIORITY_TIME_CRITICAL) != 0

    else:
        out = SetPriorityClass(pr, NORMAL_PRIORITY_CLASS) != 0
        out &= SetThreadPriority(thr, THREAD_PRIORITY_NORMAL) != 0

    return out != 0


def waitForVBL():
    """Not implemented on win32 yet.
    """
    pass


def sendStayAwake():
    """Sends a signal to your system to indicate that the computer is
    in use and should not sleep. This should be sent periodically, but
    PsychoPy will send the signal by default on each screen refresh.

    Added: v1.79.00

    Currently supported on: windows, macOS.
    """
    code = ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED
    success = SetThreadExecutionState(code)
    return success
