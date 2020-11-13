#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Part of the PsychoPy library
# Copyright (C) 2002-2018 Jonathan Peirce (C) 2019-2020 Open Science Tools Ltd.
# Distributed under the terms of the GNU General Public License (GPL).

from __future__ import absolute_import, print_function

from builtins import str
from os import path
from psychopy.experiment.components import BaseVisualComponent, Param, getInitVals, _translate
from psychopy import logging

# the absolute path to the folder containing this path
thisFolder = path.abspath(path.dirname(__file__))
iconFile = path.join(thisFolder, 'brush.png')
tooltip = _translate('Brush: a drawing tool')

# only use _localized values for label values, nothing functional:
_localized = {'lineColorSpace': _translate('Line color-space'),
              'lineColor': _translate('Line color'),
              'lineWidth': _translate('Line width'),
              'opacity': _translate('Opacity'),
              'buttonRequired':_translate('Press button')
              }

class BrushComponent(BaseVisualComponent):
    """A class for drawing freehand responses"""

    categories = ['Responses']

    def __init__(self, exp, parentName, name='brush',
                 lineColor='$[1,1,1]', lineColorSpace='rgb',
                 lineWidth=1.5, opacity=1,
                 buttonRequired=True,
                 startType='time (s)', startVal=0.0,
                 stopType='duration (s)', stopVal=1.0,
                 startEstim='', durationEstim=''):
        super(BrushComponent, self).__init__(
            exp, parentName, name=name,
            startType=startType, startVal=startVal,
            stopType=stopType, stopVal=stopVal,
            startEstim=startEstim, durationEstim=durationEstim)

        self.type = 'Brush'
        self.url = "http://www.psychopy.org/builder/components/brush.html"
        self.exp.requirePsychopyLibs(['visual'])
        self.targets = ['PsychoPy', 'PsychoJS']
        self.order = ['lineWidth', 'opacity', 'buttonRequired']

        del self.params['color']  # because color is defined by lineColor
        del self.params['colorSpace']
        del self.params['size']  # because size determined by lineWidth
        del self.params['ori']
        del self.params['pos']
        del self.params['units']  # always in pix

        # params
        msg = _translate("Line color of this brush; Right-click to bring"
                         " up a color-picker (rgb only)")
        self.params['lineColor'] = Param(
            lineColor, valType='str', allowedTypes=[],
            updates='constant',
            allowedUpdates=['constant', 'set every repeat'],
            hint=msg,
            label=_localized['lineColor'], categ='Advanced')

        msg = _translate("Width of the brush's line (always in pixels and limited to 10px max width)")
        self.params['lineWidth'] = Param(
            lineWidth, valType='code', allowedTypes=[],
            updates='constant',
            allowedUpdates=['constant', 'set every repeat'],
            hint=msg,
            label=_localized['lineWidth'])

        msg = _translate("Choice of color space for the fill color "
                         "(rgb, dkl, lms, hsv)")
        self.params['lineColorSpace'] = Param(
            lineColorSpace, valType='str',
            allowedVals=['rgb', 'dkl', 'lms', 'hsv'],
            updates='constant',
            hint=msg,
            label=_localized['lineColorSpace'], categ='Advanced')

        msg = _translate("The line opacity")
        self.params['opacity'] = Param(
            opacity, valType='code', allowedTypes=[],
            updates='constant',
            allowedUpdates=['constant', 'set every repeat'],
            hint=msg,
            label=_localized['opacity'])

        msg = _translate("Whether a button needs to be pressed to draw (True/False)")
        self.params['buttonRequired'] = Param(
            buttonRequired, valType='code', allowedTypes=[],
            updates='constant',
            allowedUpdates=['constant', 'set every repeat'],
            hint=msg,
            label=_localized['buttonRequired'], categ='Advanced')

    def writeInitCode(self, buff):
        params = getInitVals(self.params)
        code = ("{name} = visual.Brush(win=win, name='{name}',\n"
                "   lineWidth={lineWidth},\n"
                "   lineColor={lineColor},\n"
                "   lineColorSpace={lineColorSpace},\n"
                "   opacity={opacity},\n"
                "   buttonRequired={buttonRequired})").format(name=params['name'],
                                                lineWidth=params['lineWidth'],
                                                lineColor=params['lineColor'],
                                                lineColorSpace=params['lineColorSpace'],
                                                opacity=params['opacity'],
                                                buttonRequired=params['buttonRequired'])
        buff.writeIndentedLines(code)

    def writeInitCodeJS(self, buff):
        # JS code does not use Brush class
        params = getInitVals(self.params)

        code = ("{name} = {{}};\n"
                "get{name} = function() {{\n"
                "  return ( new visual.ShapeStim({{\n"
                "    win: psychoJS.window,\n"
                "    vertices: [[0, 0]],\n"
                "    lineWidth: {lineWidth},\n"
                "    lineColor: new util.Color({lineColor}),\n"
                "    opacity: {opacity},\n"
                "    closeShape: false,\n"
                "    autoLog: false\n"
                "    }}))\n"
                "}}\n\n").format(name=params['name'],
                                 lineWidth=params['lineWidth'],
                                 lineColor=params['lineColor'],
                                 opacity=params['opacity'])

        buff.writeIndentedLines(code)
        # add reset function
        code = ("{name}Reset = {name}.reset = function() {{\n"
                "  if ({name}Shapes.length > 0) {{\n"
                "    for (let shape of {name}Shapes) {{\n"
                "      shape.setAutoDraw(false);\n"
                "    }}\n"
                "  }}\n"
                "  {name}AtStartPoint = false;\n"
                "  {name}Shapes = [];\n"
                "  {name}CurrentShape = -1;\n"
                "}}\n\n").format(name=params['name'])
        buff.writeIndentedLines(code)

        # Define vars for drawing
        code = ("{name}CurrentShape = -1;\n"
                "{name}BrushPos = [];\n"
                "{name}Pointer = new core.Mouse({{win: psychoJS.window}});\n"
                "{name}AtStartPoint = false;\n"
                "{name}Shapes = [];\n").format(name=params['name'])
        buff.writeIndentedLines(code)

    def writeRoutineStartCode(self, buff):
        # Write update code
        super(BrushComponent, self).writeRoutineStartCode(buff)
        # Reset shapes for each trial
        buff.writeIndented("{}.reset()\n".format(self.params['name']))

    def writeRoutineStartCodeJS(self, buff):
        # Write update code
        # super(BrushComponent, self).writeRoutineStartCodeJS(buff)
        # Reset shapes for each trial
        buff.writeIndented("{}Reset();\n".format(self.params['name']))

    def writeFrameCodeJS(self, buff):
        code = ("if ({name}Pointer.getPressed()[0] === 1 && {name}AtStartPoint != true) {{\n"
                "  {name}AtStartPoint = true;\n"
                "  {name}BrushPos = [];\n"
                "  {name}Shapes.push(get{name}());\n"
                "  {name}CurrentShape += 1;\n"
                "  {name}Shapes[{name}CurrentShape].setAutoDraw(true);\n"
                "}}\n"
                "if ({name}Pointer.getPressed()[0] === 1) {{\n"
                "  {name}BrushPos.push({name}Pointer.getPos());\n"
                "  {name}Shapes[{name}CurrentShape].setVertices({name}BrushPos);\n"
                "}} else {{\n"
                "  {name}AtStartPoint = false;\n"
                "}}\n".format(name=self.params['name']))
        buff.writeIndentedLines(code)
