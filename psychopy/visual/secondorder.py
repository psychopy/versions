#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Part of the PsychoPy library
# Copyright (C) 2002-2018 Jonathan Peirce (C) 2019-2022 Open Science Tools Ltd.
# some code provided by Andrew Schofield
# Distributed under the terms of the GNU General Public License (GPL).

"""Stimulus object for drawing arbitrary bitmap carriers with an arbitrary
second-order envelope carrier and envelope can vary independently for
orientation, frequency and phase. Also does beat stimuli.

These are optional components that can be obtained by installing the
`psychopy-visionscience` extension into the current environment.

"""

import psychopy.logging as logging

try:
    from psychopy_visionscience import EnvelopeGrating
except (ModuleNotFoundError, ImportError):
    logging.error(
        "Support for `EnvelopeGrating` is not available this session. Please "
        "install `psychopy-visionscience` and restart the session to enable "
        "support.")

if __name__ == "__main__":
    pass
