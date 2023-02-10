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

# Requires shaders if you don't have them it will just throw and error.
# Ensure setting pyglet.options['debug_gl'] to False is done prior to any
# other calls to pyglet or pyglet submodules, otherwise it may not get picked
# up by the pyglet GL engine and have no effect.
# Shaders will work but require OpenGL2.0 drivers AND PyOpenGL3.0+

try:
    from psychopy_visionscience import NoiseStim
except (ModuleNotFoundError, ImportError):
    logging.error(
        "Support for `NoiseStim` is not available this session. Please install "
        "`psychopy-visionscience` and restart the session to enable support.")

if __name__ == "__main__":
    pass
