#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Part of the PsychoPy library
Copyright (C) 2002-2018 Jonathan Peirce (C) 2019-2022 Open Science Tools Ltd.
Distributed under the terms of the GNU General Public License (GPL).
"""

from pathlib import Path
from xml.etree.ElementTree import Element

from psychopy import prefs
from psychopy.constants import FOREVER
from ..params import Param
from psychopy.experiment.utils import CodeGenerationException
from psychopy.experiment.utils import unescapedDollarSign_re
from psychopy.experiment.params import getCodeFromParamStr
from psychopy.alerts import alerttools
from psychopy.colors import nonAlphaSpaces

from psychopy.localization import _translate, _localized


class BaseComponent:
    """A template for components, defining the methods to be overridden"""
    # override the categories property below
    # an attribute of the class, determines the section in the components panel

    categories = ['Custom']
    targets = []
    iconFile = Path(__file__).parent / "unknown" / "unknown.png"
    tooltip = ""

    def __init__(self, exp, parentName, name='',
                 startType='time (s)', startVal='',
                 stopType='duration (s)', stopVal='',
                 startEstim='', durationEstim='',
                 saveStartStop=True, syncScreenRefresh=False,
                 disabled=False):
        self.type = 'Base'
        self.exp = exp  # so we can access the experiment if necess
        self.parentName = parentName  # to access the routine too if needed

        self.params = {}
        self.depends = []  # allows params to turn each other off/on
        """{
         "dependsOn": "shape",
         "condition": "=='n vertices",
         "param": "n vertices",
         "true": "enable",  # what to do with param if condition is True
         "false": "disable",  # permitted: hide, show, enable, disable
         }"""
        self.order = ['name', 'startVal', 'startEstim', 'startType', 'stopVal', 'durationEstim', 'stopType']  # name first, then timing, then others

        msg = _translate(
            "Name of this component (alphanumeric or _, no spaces)")
        self.params['name'] = Param(name,
            valType='code', inputType="single", categ='Basic',
            hint=msg,
            label=_localized['name'])

        msg = _translate("How do you want to define your start point?")
        self.params['startType'] = Param(startType,
            valType='str', inputType="choice", categ='Basic',
            allowedVals=['time (s)', 'frame N', 'condition'],
            hint=msg, direct=False,
            label=_localized['startType'])

        msg = _translate("How do you want to define your end point?")
        self.params['stopType'] = Param(stopType,
            valType='str', inputType="choice", categ='Basic',
            allowedVals=['duration (s)', 'duration (frames)', 'time (s)',
                         'frame N', 'condition'],
            hint=msg, direct=False,
            label=_localized['stopType'])

        self.params['startVal'] = Param(startVal,
            valType='code', inputType="single", categ='Basic',
            hint=_translate("When does the component start?"), allowedTypes=[],
            label=_localized['startVal'])

        self.params['stopVal'] = Param(stopVal,
            valType='code', inputType="single", categ='Basic',
            updates='constant', allowedUpdates=[], allowedTypes=[],
            hint=_translate("When does the component end? (blank is endless)"),
            label=_localized['stopVal'])

        msg = _translate("(Optional) expected start (s), purely for "
                         "representing in the timeline")
        self.params['startEstim'] = Param(startEstim,
            valType='code', inputType="single", categ='Basic',
            hint=msg, allowedTypes=[], direct=False,
            label=_localized['startEstim'])

        msg = _translate("(Optional) expected duration (s), purely for "
                         "representing in the timeline")
        self.params['durationEstim'] = Param(durationEstim,
            valType='code', inputType="single", categ='Basic',
            hint=msg, allowedTypes=[], direct=False,
            label=_localized['durationEstim'])

        msg = _translate("Store the onset/offset times in the data file "
                         "(as well as in the log file).")
        self.params['saveStartStop'] = Param(saveStartStop,
            valType='bool', inputType="bool", categ='Data',
            hint=msg, allowedTypes=[],
            label=_translate('Save onset/offset times'))

        msg = _translate("Synchronize times with screen refresh (good for "
                         "visual stimuli and responses based on them)")
        self.params['syncScreenRefresh'] = Param(syncScreenRefresh,
            valType='bool', inputType="bool", categ="Data",
            hint=msg, allowedTypes=[],
            label=_translate('Sync timing with screen refresh'))

        msg = _translate("Disable this component")
        self.params['disabled'] = Param(disabled,
            valType='bool', inputType="bool", categ="Testing",
            hint=msg, allowedTypes=[], direct=False,
            label=_translate('Disable component'))

    @property
    def _xml(self):
        # Make root element
        element = Element(self.__class__.__name__)
        element.set("name", self.params['name'].val)
        # Add an element for each parameter
        for key, param in sorted(self.params.items()):
            # Create node
            paramNode = param._xml
            paramNode.set("name", key)
            # Add node
            element.append(paramNode)

        return element

    def __repr__(self):
        _rep = "psychopy.experiment.components.%s(name='%s', exp=%s)"
        return _rep % (self.__class__.__name__, self.name, self.exp)

    def integrityCheck(self):
        """
        Run component integrity checks for non-visual components
        """
        alerttools.testDisabled(self)
        alerttools.testStartEndTiming(self)

    def _dubiousConstantUpdates(self):
        """Return a list of fields in component that are set to be constant
        but seem intended to be dynamic. Some code fields are constant, and
        some denoted as code by $ are constant.
        """
        warnings = []
        # treat expInfo as likely to be constant; also treat its keys as
        # constant because its handy to make a short-cut in code:
        # exec(key+'=expInfo[key]')
        expInfo = self.exp.settings.getInfo()
        keywords = self.exp.namespace.nonUserBuilder[:]
        keywords.extend(['expInfo'] + list(expInfo.keys()))
        reserved = set(keywords).difference({'random', 'rand'})
        for key in self.params:
            field = self.params[key]
            if (not hasattr(field, 'val') or
                    not isinstance(field.val, str)):
                continue  # continue == no problem, no warning
            if not (field.allowedUpdates and
                    isinstance(field.allowedUpdates, list) and
                    len(field.allowedUpdates) and
                    field.updates == 'constant'):
                continue
            # now have only non-empty, possibly-code, and 'constant' updating
            if field.valType == 'str':
                if not bool(unescapedDollarSign_re.search(field.val)):
                    continue
                code = getCodeFromParamStr(field.val)
            elif field.valType == 'code':
                code = field.val
            else:
                continue
            # get var names in the code; no names == constant
            try:
                names = compile(code, '', 'eval').co_names
            except SyntaxError:
                continue
            # ignore reserved words:
            if not set(names).difference(reserved):
                continue
            warnings.append((field, key))
        return warnings or [(None, None)]

    def writeInitCode(self, buff):
        """Write any code that a component needs that should only ever be done
        at start of an experiment, BEFORE window creation.
        """
        pass

    def writeStartCode(self, buff):
        """Write any code that a component needs that should only ever be done
        at start of an experiment, AFTER window creation.
        """
        # e.g., create a data subdirectory unique to that component type.
        # Note: settings.writeStartCode() is done first, then
        # Routine.writeStartCode() will call this method for each component in
        # each routine
        pass

    def writeFrameCode(self, buff):
        """Write the code that will be called every frame
        """
        pass

    def writeRoutineStartCode(self, buff):
        """Write the code that will be called at the beginning of
        a routine (e.g. to update stimulus parameters)
        """
        self.writeParamUpdates(buff, 'set every repeat')

    def writeRoutineStartCodeJS(self, buff):
        """Same as writeRoutineStartCode, but for JS
        """
        self.writeParamUpdatesJS(buff, 'set every repeat')

    def writeRoutineEndCode(self, buff):
        """Write the code that will be called at the end of
        a routine (e.g. to save data)
        """
        if 'saveStartStop' in self.params and self.params['saveStartStop'].val:

            # what loop are we in (or thisExp)?
            if len(self.exp.flow._loopList):
                currLoop = self.exp.flow._loopList[-1]  # last (outer-most) loop
            else:
                currLoop = self.exp._expHandler

            if 'Stair' in currLoop.type and buff.target == 'PsychoPy':
                addDataFunc = 'addOtherData'
            elif 'Stair' in currLoop.type and buff.target == 'PsychoJS':
                addDataFunc = 'psychojs.experiment.addData'
            else:
                addDataFunc = 'addData'

            loop = currLoop.params['name']
            name = self.params['name']

    def writeRoutineEndCodeJS(self, buff):
        """Write the code that will be called at the end of
        a routine (e.g. to save data)
        """
        pass

    def writeExperimentEndCode(self, buff):
        """Write the code that will be called at the end of
        an experiment (e.g. save log files or reset hardware)
        """
        pass

    def writeStartTestCode(self, buff):
        """Test whether we need to start
        """
        if self.params['syncScreenRefresh']:
            tCompare = 'tThisFlip'
        else:
            tCompare = 't'
        params = self.params
        t = tCompare
        if self.params['startType'].val == 'time (s)':
            # if startVal is an empty string then set to be 0.0
            if (isinstance(self.params['startVal'].val, str) and
                    not self.params['startVal'].val.strip()):
                self.params['startVal'].val = '0.0'
            code = (f"if {params['name']}.status == NOT_STARTED and "
                    f"{t} >= {params['startVal']}-frameTolerance:\n")
        elif self.params['startType'].val == 'frame N':
            code = (f"if {params['name']}.status == NOT_STARTED and "
                    f"frameN >= {params['startVal']}:\n")
        elif self.params['startType'].val == 'condition':
            code = (f"if {params['name']}.status == NOT_STARTED and "
                    f"{params['startVal']}:\n")
        else:
            msg = f"Not a known startType ({params['startVal']}) for {params['name']}"
            raise CodeGenerationException(msg % self.params)

        buff.writeIndented(code)

        buff.setIndentLevel(+1, relative=True)
        params = self.params
        code = (f"# keep track of start time/frame for later\n"
                f"{params['name']}.frameNStart = frameN  # exact frame index\n"
                f"{params['name']}.tStart = t  # local t and not account for scr refresh\n"
                f"{params['name']}.tStartRefresh = tThisFlipGlobal  # on global time\n"
                )
        if self.type != "Sound":
            # for sounds, don't update to actual frame time because it will start
            # on the *expected* time of the flip
            code += (f"win.timeOnFlip({params['name']}, 'tStartRefresh')"
                     f"  # time at next scr refresh\n")
        if self.params['saveStartStop']:
            code += f"# add timestamp to datafile\n"
            if self.type=='Sound' and self.params['syncScreenRefresh']:
                # use the time we *expect* the flip
                code += f"thisExp.addData('{params['name']}.started', tThisFlipGlobal)\n"
            elif 'syncScreenRefresh' in self.params and self.params['syncScreenRefresh']:
                # use the time we *detect* the flip (in the future)
                code += f"thisExp.timestampOnFlip(win, '{params['name']}.started')\n"
            else:
                # use the time ignoring any flips
                code += f"thisExp.addData('{params['name']}.started', t)\n"
        buff.writeIndentedLines(code)

    def writeStartTestCodeJS(self, buff):
        """Test whether we need to start
        """
        params = self.params
        if self.params['startType'].val == 'time (s)':
            # if startVal is an empty string then set to be 0.0
            if (isinstance(self.params['startVal'].val, str) and
                    not self.params['startVal'].val.strip()):
                self.params['startVal'].val = '0.0'
            code = (f"if (t >= {params['startVal']} "
                    f"&& {params['name']}.status === PsychoJS.Status.NOT_STARTED) {{\n")
        elif self.params['startType'].val == 'frame N':
            code = (f"if (frameN >= {params['startVal']} "
                    f"&& {params['name']}.status === PsychoJS.Status.NOT_STARTED) {{\n")
        elif self.params['startType'].val == 'condition':
            code = (f"if (({params['startVal']}) "
                    f"&& {params['name']}.status === PsychoJS.Status.NOT_STARTED) {{\n")
        else:
            msg = f"Not a known startType ({params['startVal']}) for {params['name']}"
            raise CodeGenerationException(msg)

        buff.writeIndented(code)

        buff.setIndentLevel(+1, relative=True)
        code = (f"// keep track of start time/frame for later\n"
                f"{params['name']}.tStart = t;  // (not accounting for frame time here)\n"
                f"{params['name']}.frameNStart = frameN;  // exact frame index\n\n")
        buff.writeIndentedLines(code)

    def writeStopTestCode(self, buff):
        """Test whether we need to stop
        """
        params = self.params
        buff.writeIndentedLines(f"if {params['name']}.status == STARTED:\n")
        buff.setIndentLevel(+1, relative=True)

        # If start time is blank ad stop is a duration, raise alert
        if self.params['stopType'] in ('duration (s)', 'duration (frames)'):
            if ('startVal' not in self.params) or (self.params['startVal'] in ("", "None", None)):
                alerttools.alert(4120, strFields={'component': self.params['name']})

        if self.params['stopType'].val == 'time (s)':
            code = (f"# is it time to stop? (based on local clock)\n"
                    f"if tThisFlip > {params['stopVal']}-frameTolerance:\n"
                    )
        # duration in time (s)
        elif (self.params['stopType'].val == 'duration (s)'):
            code = (f"# is it time to stop? (based on global clock, using actual start)\n"
                    f"if tThisFlipGlobal > {params['name']}.tStartRefresh + {params['stopVal']}-frameTolerance:\n")
        elif self.params['stopType'].val == 'duration (frames)':
            code = (f"if frameN >= ({params['name']}.frameNStart + {params['stopVal']}):\n")
        elif self.params['stopType'].val == 'frame N':
            code = f"if frameN >= {params['stopVal']}:\n"
        elif self.params['stopType'].val == 'condition':
            code = f"if bool({params['stopVal']}):\n"
        else:
            msg = (f"Didn't write any stop line for startType={params['startType']}, "
                   f"stopType={params['stopType']}")
            raise CodeGenerationException(msg)

        buff.writeIndentedLines(code)
        buff.setIndentLevel(+1, relative=True)
        code = (f"# keep track of stop time/frame for later\n"
                f"{params['name']}.tStop = t  # not accounting for scr refresh\n"
                f"{params['name']}.frameNStop = frameN  # exact frame index\n"
                )
        if self.params['saveStartStop']:
            code += f"# add timestamp to datafile\n"
            if 'syncScreenRefresh' in self.params and self.params['syncScreenRefresh']:
                # use the time we *detect* the flip (in the future)
                code += f"thisExp.timestampOnFlip(win, '{params['name']}.stopped')\n"
            else:
                # use the time ignoring any flips
                code += f"thisExp.addData('{params['name']}.stopped', t)\n"
        buff.writeIndentedLines(code)

    def writeStopTestCodeJS(self, buff):
        """Test whether we need to stop
        """
        params = self.params
        if self.params['stopType'].val == 'time (s)':
            code = (f"frameRemains = {params['stopVal']} "
                    f" - psychoJS.window.monitorFramePeriod * 0.75;"
                    f"  // most of one frame period left\n"
                    f"if (({params['name']}.status === PsychoJS.Status.STARTED || {params['name']}.status === PsychoJS.Status.FINISHED) "
                    f"&& t >= frameRemains) {{\n")
        # duration in time (s)
        elif (self.params['stopType'].val == 'duration (s)' and
              self.params['startType'].val == 'time (s)'):
            code = (f"frameRemains = {params['startVal']} + {params['stopVal']}"
                    f" - psychoJS.window.monitorFramePeriod * 0.75;"
                    f"  // most of one frame period left\n"
                    f"if ({params['name']}.status === PsychoJS.Status.STARTED "
                    f"&& t >= frameRemains) {{\n")
        # start at frame and end with duratio (need to use approximate)
        elif self.params['stopType'].val == 'duration (s)':
            code = (f"if ({params['name']}.status === PsychoJS.Status.STARTED "
                    f"&& t >= ({params['name']}.tStart + {params['stopVal']})) {{\n")
        elif self.params['stopType'].val == 'duration (frames)':
            code = (f"if ({params['name']}.status === PsychoJS.Status.STARTED "
                    f"&& frameN >= ({params['name']}.frameNStart + {params['stopVal']})) {{\n")
        elif self.params['stopType'].val == 'frame N':
            code = (f"if ({params['name']}.status === PsychoJS.Status.STARTED "
                    f"&& frameN >= {params['stopVal']}) {{\n")
        elif self.params['stopType'].val == 'condition':
            code = (f"if ({params['name']}.status === PsychoJS.Status.STARTED "
                    f"&& Boolean({params['stopVal']})) {{\n")
        else:
            msg = (f"Didn't write any stop line for startType="
                   f"{params['startType']}, "
                   f"stopType={params['stopType']}")
            raise CodeGenerationException(msg)

        buff.writeIndentedLines(code)
        buff.setIndentLevel(+1, relative=True)

    def writeParamUpdates(self, buff, updateType, paramNames=None,
                          target="PsychoPy"):
        """write updates to the buffer for each parameter that needs it
        updateType can be 'experiment', 'routine' or 'frame'
        """
        if paramNames is None:
            paramNames = list(self.params.keys())
        for thisParamName in paramNames:
            if thisParamName == 'advancedParams':
                continue  # advancedParams is not really a parameter itself
            thisParam = self.params[thisParamName]
            if thisParam.updates == updateType:
                self.writeParamUpdate(
                    buff, self.params['name'],
                    thisParamName, thisParam, thisParam.updates,
                    target=target)

    def writeParamUpdatesJS(self, buff, updateType, paramNames=None):
        """Pass this to the standard writeParamUpdates but with new 'target'
        """
        self.writeParamUpdates(buff, updateType, paramNames,
                               target="PsychoJS")

    def writeParamUpdate(self, buff, compName, paramName, val, updateType,
                         params=None, target="PsychoPy"):
        """Writes an update string for a single parameter.
        This should not need overriding for different components - try to keep
        constant
        """
        if params is None:
            params = self.params
        # first work out the name for the set____() function call
        if paramName == 'advancedParams':
            return  # advancedParams is not really a parameter itself
        elif paramName == 'letterHeight':
            paramCaps = 'Height'  # setHeight for TextStim
        elif paramName == 'image' and self.getType() == 'PatchComponent':
            paramCaps = 'Tex'  # setTex for PatchStim
        elif paramName == 'sf':
            paramCaps = 'SF'  # setSF, not SetSf
        elif paramName == 'coherence':
            paramCaps = 'FieldCoherence'
        elif paramName == 'fieldPos':
            paramCaps = 'FieldPos'
        else:
            paramCaps = paramName[0].capitalize() + paramName[1:]

        # code conversions for PsychoJS
        if target == 'PsychoJS':
            endStr = ';'
            try:
                valStr = str(val).strip()
            except TypeError:
                if isinstance(val, Param):
                    val = val.val
                raise TypeError(f"Value of parameter {paramName} of component {compName} "
                                f"could not be converted to JS. Value is {val}")
            # convert (0,0.5) to [0,0.5] but don't convert "rand()" to "rand[]"
            if valStr.startswith("(") and valStr.endswith(")"):
                valStr = valStr.replace("(", "[", 1)
                valStr = valStr[::-1].replace(")", "]", 1)[
                         ::-1]  # replace from right
            # filenames (e.g. for image) need to be loaded from resources
            if paramName in ["sound"]:
                valStr = (f"psychoJS.resourceManager.getResource({valStr})")
        else:
            endStr = ''

        # then write the line
        if updateType == 'set every frame' and target == 'PsychoPy':
            loggingStr = ', log=False'
        elif updateType == 'set every frame' and target == 'PsychoJS':
            loggingStr = ', false'  # don't give the keyword 'log' in JS
        else:
            loggingStr = ''

        if target == 'PsychoPy':
            if paramName == 'color':
                buff.writeIndented(f"{compName}.setColor({params['color']}, colorSpace={params['colorSpace']}")
                buff.write(f"{loggingStr}){endStr}\n")
            elif paramName == 'sound':
                stopVal = params['stopVal'].val
                if stopVal in ['', None, -1, 'None']:
                    stopVal = '-1'
                buff.writeIndented(f"{compName}.setSound({params['sound']}, secs={stopVal}){endStr}\n")
            elif paramName == 'movie' and params['backend'].val in ('moviepy', 'avbin', 'vlc', 'opencv'):
                # we're going to do this for now ...
                if params['units'].val == 'from exp settings':
                    unitsStr = "units=''"
                else:
                    unitsStr = "units=%(units)s" % params

                if params['backend'].val == 'moviepy':
                    code = ("%s = visual.MovieStim3(\n" % params['name'] +
                            "    win=win, name='%s', %s,\n" % (
                                params['name'], unitsStr) +
                            "    noAudio = %(No audio)s,\n" % params)
                elif params['backend'].val == 'avbin':
                    code = ("%s = visual.MovieStim(\n" % params['name'] +
                            "    win=win, name='%s', %s,\n" % (
                                params['name'], unitsStr))
                elif params['backend'].val == 'vlc':
                    code = ("%s = visual.VlcMovieStim(\n" % params['name'] +
                            "    win=win, name='%s', %s,\n" % (
                                params['name'], unitsStr))
                else:
                    code = ("%s = visual.MovieStim(\n" % params['name'] +
                            "    win=win, name='%s', %s,\n" % (
                                params['name'], unitsStr) +
                            "    noAudio=%(No audio)s,\n" % params)

                code += ("    filename=%(movie)s,\n"
                         "    ori=%(ori)s, pos=%(pos)s, opacity=%(opacity)s,\n"
                         "    loop=%(loop)s, anchor=%(anchor)s,\n"
                         % params)

                buff.writeIndentedLines(code)

                if params['size'].val != '':
                    buff.writeIndented("    size=%(size)s,\n" % params)

                depth = -self.getPosInRoutine()
                code = ("    depth=%.1f,\n"
                        "    )\n")
                buff.writeIndentedLines(code % depth)

            else:
                buff.writeIndented(f"{compName}.set{paramCaps}({val}{loggingStr}){endStr}\n")
        elif target == 'PsychoJS':
            # write the line
            if paramName == 'color':
                buff.writeIndented(f"{compName}.setColor(new util.Color({params['color']})")
                buff.write(f"{loggingStr}){endStr}\n")
            elif paramName == 'fillColor':
                buff.writeIndented(f"{compName}.setFillColor(new util.Color({params['fillColor']})")
                buff.write(f"{loggingStr}){endStr}\n")
            elif paramName == 'lineColor':
                buff.writeIndented(f"{compName}.setLineColor(new util.Color({params['lineColor']})")
                buff.write(f"{loggingStr}){endStr}\n")
            elif paramName == 'sound':
                stopVal = params['stopVal']
                if stopVal in ['', None, -1, 'None']:
                    stopVal = '-1'
                buff.writeIndented(f"{compName}.setSound({params['sound']}, secs={stopVal}){endStr}\n")
            elif paramName == 'emotiv_marker_label' or paramName == "emotiv_marker_value" or paramName == "emotiv_stop_marker":
                # This allows the eeg_marker to be updated by a code component or a conditions file
                # There is no setMarker_label or setMarker_value function in the eeg_marker object
                # The marker label and value are set by the variables set in the dialogue
                pass
            else:
                buff.writeIndented(f"{compName}.set{paramCaps}({val}{loggingStr}){endStr}\n")

    def checkNeedToUpdate(self, updateType):
        """Determine whether this component has any parameters set to repeat
        at this level

        usage::
            True/False = checkNeedToUpdate(self, updateType)

        """
        for thisParamName in self.params:
            if thisParamName == 'advancedParams':
                continue
            thisParam = self.params[thisParamName]
            if thisParam.updates == updateType:
                return True

        return False

    def getStartAndDuration(self):
        """Determine the start and duration of the stimulus
        purely for Routine rendering purposes in the app (does not affect
        actual drawing during the experiment)

        start, duration, nonSlipSafe = component.getStartAndDuration()

        nonSlipSafe indicates that the component's duration is a known fixed
        value and can be used in non-slip global clock timing (e.g for fMRI)
        """
        if not 'startType' in self.params:
            # this component does not have any start
            return None, None, True

        # deduce a start time (s) if possible
        startType = self.params['startType'].val
        numericStart = canBeNumeric(self.params['startVal'].val)

        if canBeNumeric(self.params['startEstim'].val):
            startTime = float(self.params['startEstim'].val)
        elif startType == 'time (s)' and numericStart:
            startTime = float(self.params['startVal'].val)
        else:
            startTime = None

        if 'stopType' not in self.params:
            # this component does not have any stop
            return startTime, 0, numericStart

        # deduce stop time (s) if possible
        stopType = self.params['stopType'].val
        numericStop = canBeNumeric(self.params['stopVal'].val)

        if stopType == 'time (s)' and numericStop:
            duration = float(self.params['stopVal'].val) - (startTime or 0)
        elif stopType == 'duration (s)' and numericStop:
            duration = float(self.params['stopVal'].val)
        else:
            # deduce duration (s) if possible. Duration used because component
            # time icon needs width
            if canBeNumeric(self.params['durationEstim'].val):
                duration = float(self.params['durationEstim'].val)
            elif self.params['stopVal'].val in ['', '-1', 'None']:
                duration = FOREVER  # infinite duration
            else:
                duration = None

        nonSlipSafe = numericStop and (numericStart or stopType == 'time (s)')
        return startTime, duration, nonSlipSafe

    def getPosInRoutine(self):
        """Find the index (position) in the parent Routine (0 for top)
        """
        routine = self.exp.routines[self.parentName]
        return routine.index(self)

    def getType(self):
        """Returns the name of the current object class"""
        return self.__class__.__name__

    def getShortType(self):
        """Replaces word component with empty string"""
        return self.getType().replace('Component', '')

    @property
    def name(self):
        return self.params['name'].val

    @name.setter
    def name(self, value):
        self.params['name'].val = value

    @property
    def disabled(self):
        return bool(self.params['disabled'])

    @disabled.setter
    def disabled(self, value):
        self.params['disabled'].val = value

    @property
    def currentLoop(self):
        # Get list of active loops
        loopList = self.exp.flow._loopList

        if len(loopList):
            # If there are any active loops, return the highest level
            return self.exp.flow._loopList[-1].params['name']
        else:
            # Otherwise, we are not in a loop, so loop handler is just experiment handler
            return "thisExp"


class BaseVisualComponent(BaseComponent):
    """Base class for most visual stimuli
    """

    categories = ['Stimuli']
    targets = []
    iconFile = Path(__file__).parent / "unknown" / "unknown.png"
    tooltip = ""

    def __init__(self, exp, parentName, name='',
                 units='from exp settings', color='white', fillColor="", borderColor="",
                 pos=(0, 0), size=(0, 0), ori=0, colorSpace='rgb', opacity="", contrast=1,
                 startType='time (s)', startVal='',
                 stopType='duration (s)', stopVal='',
                 startEstim='', durationEstim='',
                 saveStartStop=True, syncScreenRefresh=True):

        super(BaseVisualComponent, self).__init__(
            exp, parentName, name,
            startType=startType, startVal=startVal,
            stopType=stopType, stopVal=stopVal,
            startEstim=startEstim, durationEstim=durationEstim,
            saveStartStop=saveStartStop,
            syncScreenRefresh=syncScreenRefresh)

        self.exp.requirePsychopyLibs(
            ['visual'])  # needs this psychopy lib to operate

        self.order += [
            "color",
            "fillColor",
            "borderColor",
            "colorSpace",
            "opacity",
            "size",
            "pos",
            "units",
            "anchor",
            "ori",
        ]

        msg = _translate("Units of dimensions for this stimulus")
        self.params['units'] = Param(units,
            valType='str', inputType="choice", categ='Layout',
            allowedVals=['from exp settings', 'deg', 'cm', 'pix', 'norm',
                         'height', 'degFlatPos', 'degFlat'],
            hint=msg,
            label=_localized['units'])

        msg = _translate("Foreground color of this stimulus (e.g. $[1,1,0], red )")
        self.params['color'] = Param(color,
            valType='color', inputType="color", categ='Appearance',
            allowedTypes=[],
            updates='constant',
            allowedUpdates=['constant', 'set every repeat', 'set every frame'],
            hint=msg,
            label=_localized['color'])

        msg = _translate("In what format (color space) have you specified "
                         "the colors? (rgb, dkl, lms, hsv)")
        self.params['colorSpace'] = Param(colorSpace,
            valType='str', inputType="choice", categ='Appearance',
            allowedVals=['rgb', 'dkl', 'lms', 'hsv'],
            updates='constant',
            hint=msg,
            label=_localized['colorSpace'])

        msg = _translate("Fill color of this stimulus (e.g. $[1,1,0], red )")
        self.params['fillColor'] = Param(fillColor,
            valType='color', inputType="color", categ='Appearance',
            updates='constant', allowedTypes=[],
            allowedUpdates=['constant', 'set every repeat', 'set every frame'],
            hint=msg,
            label=_localized['fillColor'])

        msg = _translate("Color of this stimulus (e.g. $[1,1,0], red )")
        self.params['borderColor'] = Param(borderColor,
            valType='color', inputType="color", categ='Appearance',
            updates='constant',allowedTypes=[],
            allowedUpdates=['constant', 'set every repeat', 'set every frame'],
            hint=msg,
            label=_localized['borderColor'])

        msg = _translate("Opacity of the stimulus (1=opaque, 0=fully transparent, 0.5=translucent). "
                         "Leave blank for each color to have its own opacity (recommended if any color is None).")
        self.params['opacity'] = Param(opacity,
            valType='num', inputType="single", categ='Appearance',
            updates='constant', allowedTypes=[],
            allowedUpdates=['constant', 'set every repeat', 'set every frame'],
            hint=msg,
            label=_localized['opacity'])

        msg = _translate("Contrast of the stimulus (1.0=unchanged contrast, "
                         "0.5=decrease contrast, 0.0=uniform/no contrast, "
                         "-0.5=slightly inverted, -1.0=totally inverted)")
        self.params['contrast'] = Param(contrast,
            valType='num', inputType='single', allowedTypes=[], categ='Appearance',
            updates='constant',
            allowedUpdates=['constant', 'set every repeat', 'set every frame'],
            hint=msg,
            label=_localized['contrast'])

        msg = _translate("Position of this stimulus (e.g. [1,2] )")
        self.params['pos'] = Param(pos,
            valType='list', inputType="single", categ='Layout',
            updates='constant', allowedTypes=[],
            allowedUpdates=['constant', 'set every repeat', 'set every frame'],
            hint=msg,
            label=_localized['pos'])

        msg = _translate("Size of this stimulus (either a single value or "
                         "x,y pair, e.g. 2.5, [1,2] ")
        self.params['size'] = Param(size,
            valType='list', inputType="single", categ='Layout',
            updates='constant', allowedTypes=[],
            allowedUpdates=['constant', 'set every repeat', 'set every frame'],
            hint=msg,
            label=_localized['size'])

        self.params['ori'] = Param(ori,
            valType='num', inputType="spin", categ='Layout',
            updates='constant', allowedTypes=[], allowedVals=[-360,360],
            allowedUpdates=['constant', 'set every repeat', 'set every frame'],
            hint=_translate("Orientation of this stimulus (in deg)"),
            label=_localized['ori'])

        self.params['syncScreenRefresh'].readOnly = True

    def integrityCheck(self):
        """
        Run component integrity checks.
        """
        super().integrityCheck()  # run parent class checks first

        win = alerttools.TestWin(self.exp)

        # get units for this stimulus
        if 'units' in self.params:  # e.g. BrushComponent doesn't have this
            units = self.params['units'].val
        else:
            units = None
        if units == 'use experiment settings':
            units = self.exp.settings.params[
                'Units'].val  # this 1 uppercase
        if not units or units == 'use preferences':
            units = prefs.general['units']

        # tests for visual stimuli
        alerttools.testSize(self, win, units)
        alerttools.testPos(self, win, units)
        alerttools.testAchievableVisualOnsetOffset(self)
        alerttools.testValidVisualStimTiming(self)
        alerttools.testFramesAsInt(self)

    def writeFrameCode(self, buff):
        """Write the code that will be called every frame
        """
        params = self.params
        buff.writeIndented(f"\n")
        buff.writeIndented(f"# *{params['name']}* updates\n")
        # writes an if statement to determine whether to draw etc
        self.writeStartTestCode(buff)
        buff.writeIndented(f"{params['name']}.setAutoDraw(True)\n")
        # to get out of the if statement
        buff.setIndentLevel(-1, relative=True)

        # test for stop (only if there was some setting for duration or stop)
        if self.params['stopVal'].val not in ('', None, -1, 'None'):
            # writes an if statement to determine whether to draw etc
            self.writeStopTestCode(buff)
            buff.writeIndented(f"{params['name']}.setAutoDraw(False)\n")
            # to get out of the if statement
            buff.setIndentLevel(-2, relative=True)

        # set parameters that need updating every frame
        # do any params need updating? (this method inherited from _base)
        if self.checkNeedToUpdate('set every frame'):
            buff.writeIndented(f"if {params['name']}.status == STARTED:  # only update if drawing\n")
            buff.setIndentLevel(+1, relative=True)  # to enter the if block
            self.writeParamUpdates(buff, 'set every frame')
            buff.setIndentLevel(-1, relative=True)  # to exit the if block

    def writeFrameCodeJS(self, buff):
        """Write the code that will be called every frame
        """
        params = self.params
        if "PsychoJS" not in self.targets:
            buff.writeIndented(f"// *{params['name']}* not supported by PsychoJS\n")
            return

        buff.writeIndentedLines(f"\n// *{params['name']}* updates\n")
        # writes an if statement to determine whether to draw etc
        self.writeStartTestCodeJS(buff)
        buff.writeIndented(f"{params['name']}.setAutoDraw(true);\n")
        # to get out of the if statement
        buff.setIndentLevel(-1, relative=True)
        buff.writeIndented("}\n\n")

        # test for stop (only if there was some setting for duration or stop)
        if self.params['stopVal'].val not in ('', None, -1, 'None'):
            # writes an if statement to determine whether to draw etc
            self.writeStopTestCodeJS(buff)
            buff.writeIndented(f"{params['name']}.setAutoDraw(false);\n")
            # to get out of the if statement
            buff.setIndentLevel(-1, relative=True)
            buff.writeIndented("}\n")

        # set parameters that need updating every frame
        # do any params need updating? (this method inherited from _base)
        if self.checkNeedToUpdate('set every frame'):
            buff.writeIndentedLines(f"\nif ({params['name']}.status === PsychoJS.Status.STARTED){{ "
                                    f"// only update if being drawn\n")
            buff.setIndentLevel(+1, relative=True)  # to enter the if block
            self.writeParamUpdatesJS(buff, 'set every frame')
            buff.setIndentLevel(-1, relative=True)  # to exit the if block
            buff.writeIndented("}\n")


def canBeNumeric(inStr):
    """Determines whether the input can be converted to a float
    (using a try: float(instr))
    """
    try:
        float(inStr)
        return True
    except Exception:
        return False
