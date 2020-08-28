#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Part of the PsychoPy library
# Copyright (C) 2002-2018 Jonathan Peirce (C) 2019-2020 Open Science Tools Ltd.
# Distributed under the terms of the GNU General Public License (GPL).

from __future__ import absolute_import, print_function
from builtins import super  # provides Py3-style super() using python-future

from builtins import str
from builtins import map
from os import path
import re
from psychopy.experiment.components import BaseComponent, Param, _translate

__author__ = 'Jeremy Gray'

# the absolute path to the folder containing this path
thisFolder = path.abspath(path.dirname(__file__))
iconFile = path.join(thisFolder, 'ratingscale.png')
tooltip = _translate('Rating scale: obtain numerical or categorical '
                     'responses')

# only use _localized values for label values, nothing functional:
_localized = {'visualAnalogScale': _translate('Visual analog scale'),
              'categoryChoices': _translate('Category choices'),
              'scaleDescription': _translate('Scale description'),
              'low': _translate('Lowest value'),
              'high': _translate('Highest value'),
              'labels': _translate('Labels'),
              'marker': _translate('Marker type'),
              'markerStart': _translate('Marker start'),
              'size': _translate('Size'),
              'pos': _translate('Position [x,y]'),
              'tickHeight': _translate('Tick height'),
              'disappear': _translate('Disappear'),
              'forceEndRoutine': _translate('Force end of Routine'),
              'showAccept': _translate('Show accept'),
              'singleClick': _translate('Single click'),
              'storeHistory': _translate('Store history'),
              'storeRating': _translate('Store rating'),
              'storeRatingTime': _translate('Store rating time'),
              'customize_everything': _translate('Customize everything :')}


class RatingScaleComponent(BaseComponent):
    """A class for presenting a rating scale as a builder component
    """
    categories = ['Responses']

    def __init__(self, exp, parentName,
                 name='rating',
                 scaleDescription='',
                 categoryChoices='',
                 visualAnalogScale=False,
                 low='1', high='7',
                 singleClick=False,
                 showAccept=True,
                 labels='',
                 size='1.0',
                 tickHeight='',
                 pos='0, -0.4',
                 startType='time (s)', startVal='0.0',
                 stopType='condition', stopVal='',
                 startEstim='', durationEstim='',
                 forceEndRoutine=True,
                 disappear=False,
                 marker='triangle',
                 markerStart='',
                 storeRating=True, storeRatingTime=True, storeHistory=False,
                 customize_everything=''):
        super(RatingScaleComponent, self).__init__(
            exp, parentName, name,
            startType=startType, startVal=startVal,
            stopType=stopType, stopVal=stopVal,
            startEstim=startEstim, durationEstim=durationEstim)
        self.type = 'RatingScale'
        self.url = "http://www.psychopy.org/builder/components/ratingscale.html"
        self.exp.requirePsychopyLibs(['visual', 'event'])

        # params
        self.order = ['name', 'visualAnalogScale', 'categoryChoices',
                      'scaleDescription', 'low', 'high', 'labels',
                      'markerStart', 'size', 'pos', 'tickHeight']

        # normal params:
        # = the usual as inherited from BaseVisual plus:
        self.params['visualAnalogScale'] = Param(
            visualAnalogScale, valType='bool', allowedTypes=[],
            updates='constant', allowedUpdates=[],
            hint=_translate("Show a continuous visual analog scale; returns"
                            " 0.00 to 1.00; takes precedence over numeric "
                            "scale or categorical choices"),
            label=_localized['visualAnalogScale'])
        self.params['categoryChoices'] = Param(
            categoryChoices, valType='str', allowedTypes=[],
            updates='constant', allowedUpdates=[],
            hint=_translate("A list of categories (non-numeric alternatives)"
                            " to present, space or comma-separated; these "
                            "take precedence over a numeric scale"),
            label=_localized['categoryChoices'])
        self.params['scaleDescription'] = Param(
            scaleDescription, valType='str', allowedTypes=[],
            updates='constant', allowedUpdates=[],
            hint=_translate("Brief instructions, such as a description of "
                            "the scale numbers as seen by the subject."),
            label=_localized['scaleDescription'])
        self.params['low'] = Param(
            low, valType='code', allowedTypes=[],
            updates='constant', allowedUpdates=[],
            hint=_translate("Lowest rating (low end of the scale); not"
                            " used for categories."),
            label=_localized['low'])
        self.params['high'] = Param(
            high, valType='code', allowedTypes=[],
            updates='constant', allowedUpdates=[],
            hint=_translate("Highest rating (top end of the scale); "
                            "not used for categories."),
            label=_localized['high'])
        self.params['labels'] = Param(
            labels, valType='str', allowedTypes=[],
            updates='constant', allowedUpdates=[],  # categ="Advanced",
            hint=_translate("Labels for the ends of the scale, "
                            "separated by commas"),
            label=_localized['labels'])
        self.params['marker'] = Param(
            marker, valType='str', allowedTypes=[],
            updates='constant', allowedUpdates=[],  # categ="Advanced",
            hint=_translate("Style for the marker: triangle, circle, glow, "
                            "slider, hover"),
            label=_localized['marker'])
        self.params['markerStart'] = Param(
            markerStart, valType='str', allowedTypes=[],
            updates='constant', allowedUpdates=[],  # categ="Advanced",
            hint=_translate("initial position for the marker"),
            label=_localized['markerStart'])

        # advanced params:
        self.params['singleClick'] = Param(
            singleClick, valType='bool', allowedTypes=[],
            updates='constant', allowedUpdates=[], categ="Advanced",
            hint=_translate("Should clicking the line accept that rating "
                            "(without needing to confirm via 'accept')?"),
            label=_localized['singleClick'])
        self.params['disappear'] = Param(
            disappear, valType='bool', allowedTypes=[],
            updates='constant', allowedUpdates=[], categ="Advanced",
            hint=_translate("Hide the scale when a rating has been accepted;"
                            " False to remain on-screen"),
            label=_localized['disappear'])
        self.params['showAccept'] = Param(
            showAccept, valType='bool', allowedTypes=[],
            updates='constant', allowedUpdates=[], categ="Advanced",
            hint=_translate("Should the accept button by visible?"),
            label=_localized['showAccept'])
        self.params['storeRating'] = Param(
            storeRating, valType='bool', allowedTypes=[],
            updates='constant', allowedUpdates=[], categ="Advanced",
            hint=_translate("store the rating"),
            label=_localized['storeRating'])
        self.params['storeRatingTime'] = Param(
            storeRatingTime, valType='bool', allowedTypes=[],
            updates='constant', allowedUpdates=[], categ="Advanced",
            hint=_translate("store the time taken to make the choice (in "
                            "seconds)"),
            label=_localized['storeRatingTime'])
        self.params['storeHistory'] = Param(
            storeHistory, valType='bool', allowedTypes=[],
            updates='constant', allowedUpdates=[], categ="Advanced",
            hint=_translate("store the history of (selection, time)"),
            label=_localized['storeHistory'])
        self.params['forceEndRoutine'] = Param(
            forceEndRoutine, valType='bool', allowedTypes=[],
            updates='constant', allowedUpdates=[], categ="Advanced",
            hint=_translate("Should accepting a rating cause the end of the "
                            "routine (e.g. trial)?"),
            label=_localized['forceEndRoutine'])
        self.params['size'] = Param(
            size, valType='code', allowedTypes=[],
            updates='constant', allowedUpdates=[], categ="Advanced",
            hint=_translate("Relative size on the screen; size > 1 is larger"
                            " than default; size < 1 is smaller"),
            label=_localized['size'])
        self.params['tickHeight'] = Param(
            tickHeight, valType='str', allowedTypes=[],
            updates='constant', allowedUpdates=[], categ="Advanced",
            hint=_translate("height of tick marks (1 is upward, 0 is hidden,"
                            " -1 is downward)"),
            label=_localized['tickHeight'])
        self.params['pos'] = Param(
            pos, valType='str', allowedTypes=[],
            updates='constant', allowedUpdates=[], categ="Advanced",
            hint=_translate("x,y position on the screen"),
            label=_localized['pos'])

        # customization:
        self.params['customize_everything'] = Param(
            customize_everything, valType='extendedStr', allowedTypes=[],
            updates='constant', allowedUpdates=[], categ="Custom",
            hint=_translate("Use this text to create the rating scale as you"
                            " would in a code component; overrides all"
                            " dialog settings except time parameters, "
                            "forceEndRoutine, storeRatingTime, storeRating"),
            label=_localized['customize_everything'])

    def writeInitCode(self, buff):
        # build up an initialization string for RatingScale():
        _in = "%(name)s = visual.RatingScale(win=win, name='%(name)s'"
        init_str = _in % self.params
        if self.params['customize_everything'].val.strip() != '':
            # clean it up a little, remove win=*, leading / trailing typos
            orig = self.params['customize_everything'].val
            custom = re.sub(r"[\\s,]*win=[^,]*,", '', orig)
            init_str += ', ' + custom.lstrip('(, ').strip('), ')
        else:
            if self.params['marker'].val:
                init_str += ', marker=%s' % repr(self.params['marker'].val)
                if self.params['marker'].val == 'glow':
                    init_str += ', markerExpansion=5'
            init_str += ", size=%s" % self.params['size']
            s = str(self.params['pos'].val)
            s = s.lstrip('([ ').strip(')] ')
            try:
                pos = list(map(float, s.split(','))) * 2
                init_str += ", pos=%s" % pos[0:2]
            except Exception:
                pass  # pos = None

            # type of scale:
            choices = str(self.params['categoryChoices'].val)
            if self.params['visualAnalogScale'].val:
                init_str += (", low=0, high=1, precision=100, "
                             "showValue=False")
                if not self.params['marker'].val:
                    init_str += ", marker='glow'"
            elif len(choices):
                if ',' in choices:
                    chc = choices.split(',')
                else:
                    chc = choices.split(' ')
                chc = [c.strip().strip(', ') for c in chc]
                init_str += ', choices=%s' % str(chc)
                if self.params['tickHeight'].val:
                    tickh = self.params['tickHeight'].val
                    init_str += ", tickHeight=%.1f" % float(tickh)
                else:
                    init_str += ", tickHeight=-1"
            else:
                # try to add low as int; but might be a var instead
                try:
                    init_str += ', low=%d' % int(self.params['low'].val)
                except ValueError:
                    if self.params['low'].val:
                        init_str += ", low=%s" % self.params['low']
                try:
                    init_str += ', high=%d' % int(self.params['high'].val)
                except ValueError:
                    if self.params['high'].val:
                        init_str += ", high=%s" % self.params['high']
                init_str += ', labels=%s' % repr(
                    self.params['labels'].val.split(','))

            scale = str(self.params['scaleDescription'])
            if not len(choices) and len(scale):
                init_str += ", scale=%s" % self.params['scaleDescription']
            if self.params['singleClick'].val:
                init_str += ", singleClick=True"
            if self.params['disappear'].val:
                init_str += ", disappear=True"
            if self.params['markerStart'].val:
                init_str += ", markerStart=%s" % self.params['markerStart']
            if not len(choices) and self.params['tickHeight'].val:
                init_str += ", tickHeight=%s" % self.params['markerStart']
            if not self.params['showAccept'].val:
                init_str += ", showAccept=False"
        # write the RatingScale() instantiation code:
        init_str += ")\n"
        buff.writeIndented(init_str)

    def writeRoutineStartCode(self, buff):
        buff.writeIndented("%(name)s.reset()\n" % (self.params))

    def writeFrameCode(self, buff):
        name = self.params['name']
        buff.writeIndented("# *%(name)s* updates\n" % (self.params))
        # try to handle blank start condition gracefully:
        if not self.params['startVal'].val.strip():
            self.params['startVal'].val = 0  # time, frame
            if self.params['startType'].val == 'condition':
                self.params['startVal'].val = 'True'

        self.writeStartTestCode(buff)
        buff.writeIndented("%(name)s.setAutoDraw(True)\n" % (self.params))
        buff.setIndentLevel(-1, relative=True)

        # handle a response:
        # if requested, force end of trial when the subject 'accepts' the
        # current rating:
        if self.params['forceEndRoutine'].val:
            code = ("continueRoutine &= %s.noResponse  "
                    "# a response ends the trial\n")
            buff.writeIndented(code % name)

        # for completeness: could handle going beyond
        # self.params['stopVal'].val with no response

    def writeRoutineEndCode(self, buff):
        name = self.params['name']
        if len(self.exp.flow._loopList):
            currLoop = self.exp.flow._loopList[-1]  # last (outer-most) loop
        else:
            currLoop = self.exp._expHandler

        # write the actual code
        storeTime = self.params['storeRatingTime'].val
        if self.params['storeRating'].val or storeTime:
            if currLoop.type in ['StairHandler', 'QuestHandler']:
                msg = ("# NB PsychoPy doesn't handle a 'correct answer' "
                       "for ratingscale events so doesn't know what to "
                       "tell a StairHandler (or QuestHandler)\n")
                buff.writeIndented(msg)
            elif currLoop.type in ['TrialHandler', 'ExperimentHandler']:
                buff.writeIndented("# store data for %s (%s)\n" % (
                    currLoop.params['name'], currLoop.type))
                if self.params['storeRating'].val == True:
                    code = "%s.addData('%s.response', %s.getRating())\n"
                    buff.writeIndented(code % (currLoop.params['name'],
                                               name, name))
                if self.params['storeRatingTime'].val == True:
                    code = "%s.addData('%s.rt', %s.getRT())\n"
                    buff.writeIndented(code % (currLoop.params['name'],
                                               name, name))
                if self.params['storeHistory'].val == True:
                    code = "%s.addData('%s.history', %s.getHistory())\n"
                    buff.writeIndented(code % (currLoop.params['name'],
                                               name, name))
                if currLoop.params['name'].val == self.exp._expHandler.name:
                    buff.writeIndented("%s.nextEntry()\n" %
                                       self.exp._expHandler.name)
            else:
                buff.writeIndented("# RatingScaleComponent: unknown loop "
                                   "type, not saving any data.\n")

        # get parent to write code too (e.g. store onset/offset times)
        super().writeRoutineEndCode(buff)
