#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Part of the PsychoPy library
# Copyright (C) 2002-2018 Jonathan Peirce (C) 2019-2022 Open Science Tools Ltd.
# Distributed under the terms of the GNU General Public License (GPL).

"""Describes the Flow of an experiment
"""
import copy

from psychopy.constants import FOREVER
from xml.etree.ElementTree import Element
from pathlib import Path

from psychopy.experiment.components.static import StaticComponent
from psychopy.localization import _translate
from psychopy.experiment import Param


class BaseStandaloneRoutine:
    categories = ['Custom']
    targets = []
    iconFile = Path(__file__).parent / "unknown" / "unknown.png"
    tooltip = ""
    limit = float('inf')

    def __init__(self, exp, name='',
                 stopType='duration (s)', stopVal='',
                 disabled=False):
        self.params = {}
        self.name = name
        self.exp = exp
        self.type = 'StandaloneRoutine'
        self.depends = []  # allows params to turn each other off/on
        self.order = ['stopVal', 'stopType', 'name']

        msg = _translate(
            "Name of this routine (alphanumeric or _, no spaces)")
        self.params['name'] = Param(name,
                                    valType='code', inputType="single", categ='Basic',
                                    hint=msg,
                                    label=_translate('name'))

        self.params['stopVal'] = Param(stopVal,
            valType='num', inputType="single", categ='Basic',
            updates='constant', allowedUpdates=[], allowedTypes=[],
            hint=_translate("When does the routine end? (blank is endless)"),
            label=_translate('Stop'))

        msg = _translate("How do you want to define your end point?")
        self.params['stopType'] = Param(stopType,
            valType='str', inputType="choice", categ='Basic',
            allowedVals=['duration (s)', 'duration (frames)', 'condition'],
            hint=msg, direct=False,
            label=_translate('Stop Type...'))

        # Testing
        msg = _translate("Disable this routine")
        self.params['disabled'] = Param(disabled,
            valType='bool', inputType="bool", categ="Testing",
            hint=msg, allowedTypes=[], direct=False,
            label=_translate('Disable component'))

    def __repr__(self):
        _rep = "psychopy.experiment.routines.%s(name='%s', exp=%s)"
        return _rep % (self.__class__.__name__, self.name, self.exp)

    def __iter__(self):
        """Overloaded iteration behaviour - if iterated through, a standaloneRoutine returns
        itself once, so it can be treated like a regular routine"""
        self.__iterstop = False
        return self

    def __next__(self):
        """Overloaded iteration behaviour - if iterated through, a standaloneRoutine returns
        itself once, so it can be treated like a regular routine"""
        if self.__iterstop:
            # Stop after one iteration
            self.__iterstop = False
            raise StopIteration
        else:
            self.__iterstop = True
            return self

    @property
    def _xml(self):
        # Make root element
        element = Element(self.__class__.__name__)
        element.set("name", self.params['name'].val)
        # Add an element for each parameter
        for key, param in sorted(self.params.items()):
            # Create node
            paramNode = Element("Param")
            paramNode.set("name", key)
            # Assign values
            if hasattr(param, 'updates'):
                paramNode.set('updates', "{}".format(param.updates))
            if hasattr(param, 'val'):
                paramNode.set('val', u"{}".format(param.val).replace("\n", "&#10;"))
            if hasattr(param, 'valType'):
                paramNode.set('valType', param.valType)
            element.append(paramNode)

        return element

    def copy(self):
        # Create a deep copy of self
        dupe = copy.deepcopy(self)
        # ...but retain original exp reference
        dupe.exp = self.exp

        return dupe

    def writePreCode(self, buff):
        return

    def writePreCodeJS(self, buff):
        return

    def writeStartCode(self, buff):
        return

    def writeStartCodeJS(self, buff):
        return

    def writeRunOnceInitCode(self, buff):
        return

    def writeInitCode(self, buff):
        return

    def writeInitCodeJS(self, buff):
        return

    def writeMainCode(self, buff):
        return

    def writeRoutineBeginCodeJS(self, buff, modular):
        return

    def writeEachFrameCodeJS(self, buff, modular):
        return

    def writeRoutineEndCode(self, buff):
        # reset routineTimer at the *very end* of all non-nonSlip routines
        code = ('# the Routine "%s" was not non-slip safe, so reset '
                'the non-slip timer\n'
                'routineTimer.reset()\n')
        buff.writeIndentedLines(code % self.name)

    def writeRoutineEndCodeJS(self, buff, modular):
        return

    def writeExperimentEndCode(self, buff):
        return

    def writeExperimentEndCodeJS(self, buff):
        return

    def getType(self):
        return self.__class__.__name__

    def getComponentFromName(self, name):
        return None

    def getComponentFromType(self, thisType):
        return None

    def hasOnlyStaticComp(self):
        return False

    def getMaxTime(self):
        """If routine has a set duration, will return this along with True (as this routine is nonSlipSafe, i.e. has a fixed duration). Otherwise, will treat max time as 0 and will mark routine as nonSlipSafe (i.e. has a variable duration)..
        """

        # Assume max time of 0 and not nonSlipSafe
        maxTime = 0
        nonSlipSafe = False
        # If has a set duration, store set duration and mark as nonSlipSafe
        if 'stopVal' in self.params and 'stopType' in self.params:
            if self.params['stopType'] in ['duration (s)', 'duration (frames)']:
                maxTime = float(self.params['stopVal'].val or 0)
                nonSlipSafe = True

        return maxTime, nonSlipSafe

    def getStatics(self):
        return []

    @property
    def name(self):
        if hasattr(self, 'params'):
            if 'name' in self.params:
                return self.params['name'].val
        return self.type

    @name.setter
    def name(self, value):
        if hasattr(self, 'params'):
            if 'name' in self.params:
                self.params['name'].val = value

    @property
    def disabled(self):
        return bool(self.params['disabled'])

    @disabled.setter
    def disabled(self, value):
        self.params['disabled'].val = value


class Routine(list):
    """
    A Routine determines a single sequence of events, such
    as the presentation of trial. Multiple Routines might be
    used to comprise an Experiment (e.g. one for presenting
    instructions, one for trials, one for debriefing subjects).

    In practice a Routine is simply a python list of Components,
    each of which knows when it starts and stops.
    """

    targets = ["PsychoPy", "PsychoJS"]

    def __init__(self, name, exp, components=(), disabled=False):
        super(Routine, self).__init__()
        self.params = {'name': name}

        # Testing
        msg = _translate("Disable this component")
        self.params['disabled'] = Param(disabled,
            valType='bool', inputType="bool", categ="Testing",
            hint=msg, allowedTypes=[], direct=False,
            label=_translate('Disable component'))

        self.name = name
        self.exp = exp
        self._clockName = None  # for scripts e.g. "t = trialClock.GetTime()"
        self.type = 'Routine'
        list.__init__(self, list(components))

    def __repr__(self):
        _rep = "psychopy.experiment.Routine(name='%s', exp=%s, components=%s)"
        return _rep % (self.name, self.exp, str(list(self)))

    def copy(self):
        # Create a new routine with the same experiment and name as this one
        dupe = type(self)(self.name, self.exp, components=())
        # Iterate through components
        for comp in self:
            # Create a deep copy of each component...
            newComp = copy.deepcopy(comp)
            # ...but retain original exp reference
            newComp.exp = self.exp
            # Append to new routine
            dupe.append(newComp)

        return dupe

    @property
    def _xml(self):
        # Make root element
        element = Element("Routine")
        element.set("name", self.name)
        # Add each component's element
        for comp in self:
            element.append(comp._xml)

        return element

    @property
    def name(self):
        return self.params['name']

    @name.setter
    def name(self, name):
        self.params['name'] = name
        # Update references in components
        for comp in self:
            comp.parentName = name

    def integrityCheck(self):
        """Run tests on self and on all the Components inside"""
        for entry in self:
            if hasattr(entry, "integrityCheck"):
                entry.integrityCheck()

    def addComponent(self, component):
        """Add a component to the end of the routine"""
        self.append(component)

    def insertComponent(self, index, component):
        """Insert a component at some point of the routine.

        Parameters
        ----------
        index : int
            Position in the routine to insert the component.
        component : object
            Component object to insert.

        """
        try:
            self.insert(index, component)
        except IndexError:
            self.append(component)  # just insert at the end on invalid index

    def removeComponent(self, component):
        """Remove a component from the end of the routine"""
        name = component.params['name']
        self.remove(component)
        # if this is a static component, we need to remove references to it
        if isinstance(component, StaticComponent):
            for update in component.updatesList:
                # remove reference in component
                comp = self.exp.getComponentFromName(update['compName'])
                if comp:
                    param = comp.params[update['fieldName']]
                    param.updates = None
        # check if the component was using any Static Components for updates
        for thisParamName, thisParam in list(component.params.items()):
            if (hasattr(thisParam, 'updates') and
                    thisParam.updates and
                    'during:' in thisParam.updates):
                # remove the part that says 'during'
                updates = thisParam.updates.split(': ')[1]
                routine, static = updates.split('.')
                comp = self.exp.routines[routine].getComponentFromName(static)
                comp.remComponentUpdate(routine, name, thisParamName)

    def getStatics(self):
        """Return a list of Static components
        """
        statics = []
        for comp in self:
            if comp.type == 'Static':
                statics.append(comp)
        return statics

    def writePreCode(self, buff):
        """This is start of the script (before window is created)
        """
        for thisCompon in self:
            # check just in case; try to ensure backwards compatibility _base
            if hasattr(thisCompon, 'writePreCode'):
                thisCompon.writePreCode(buff)

    def writePreCodeJS(self, buff):
        """This is start of the script (before window is created)
        """
        for thisCompon in self:
            # check just in case; try to ensure backwards compatibility _base
            if hasattr(thisCompon, 'writePreCodeJS'):
                thisCompon.writePreCodeJS(buff)

    def writeStartCode(self, buff):
        """This is start of the *experiment* (after window is created)
        """
        for thisCompon in self:
            # check just in case; try to ensure backwards compatibility _base
            if hasattr(thisCompon, 'writeStartCode'):
                thisCompon.writeStartCode(buff)

    def writeStartCodeJS(self, buff):
        """This is start of the *experiment*
        """
        # few components will have this
        for thisCompon in self:
            # check just in case; try to ensure backwards compatibility _base
            if hasattr(thisCompon, 'writeStartCodeJS'):
                thisCompon.writeStartCodeJS(buff)

    def writeRunOnceInitCode(self, buff):
        """ Run once init code goes at the beginning of the script (before
        Window creation) and the code will be run only once no matter how many
        similar components request it
        """
        for thisCompon in self:
            # check just in case; try to ensure backwards compatibility _base
            if hasattr(thisCompon, 'writeRunOnceInitCode'):
                thisCompon.writeRunOnceInitCode(buff)

    def writeInitCode(self, buff):
        code = '\n# --- Initialize components for Routine "%s" ---\n'
        buff.writeIndentedLines(code % self.name)

        maxTime, useNonSlip = self.getMaxTime()
        self._clockName = 'routineTimer'
        for thisCompon in self:
            thisCompon.writeInitCode(buff)

    def writeInitCodeJS(self, buff):
        code = '// Initialize components for Routine "%s"\n'
        buff.writeIndentedLines(code % self.name)
        self._clockName = self.name + "Clock"
        buff.writeIndented('%s = new util.Clock();\n' % self._clockName)
        for thisCompon in self:
            if hasattr(thisCompon, 'writeInitCodeJS'):
                thisCompon.writeInitCodeJS(buff)

    def writeMainCode(self, buff):
        """This defines the code for the frames of a single routine
        """
        # create the frame loop for this routine
        code = ('\n# --- Prepare to start Routine "%s" ---\n')
        buff.writeIndentedLines(code % (self.name))
        code = (
            'continueRoutine = True\n'
            'routineForceEnded = False\n'
        )
        buff.writeIndentedLines(code)

        # can we use non-slip timing?
        maxTime, useNonSlip = self.getMaxTime()

        code = "# update component parameters for each repeat\n"
        buff.writeIndentedLines(code)
        # This is the beginning of the routine, before the loop starts
        for event in self:
            event.writeRoutineStartCode(buff)

        code = '# keep track of which components have finished\n'
        buff.writeIndentedLines(code)
        # Get list of components, but leave out Variable components, which may not support attributes
        compStr = ', '.join([c.params['name'].val for c in self
                             if 'startType' in c.params and c.type != 'Variable'])
        buff.writeIndented('%sComponents = [%s]\n' % (self.name, compStr))

        code = ("for thisComponent in {name}Components:\n"
                "    thisComponent.tStart = None\n"
                "    thisComponent.tStop = None\n"
                "    thisComponent.tStartRefresh = None\n"
                "    thisComponent.tStopRefresh = None\n"
                "    if hasattr(thisComponent, 'status'):\n"
                "        thisComponent.status = NOT_STARTED\n"
                "# reset timers\n"
                't = 0\n'
                '_timeToFirstFrame = win.getFutureFlipTime(clock="now")\n'
                # '{clockName}.reset(-_timeToFirstFrame)  # t0 is time of first possible flip\n'
                'frameN = -1\n'
                '\n# --- Run Routine "{name}" ---\n')
        buff.writeIndentedLines(code.format(name=self.name,
                                            clockName=self._clockName))
        if useNonSlip:
            code = f'while continueRoutine and routineTimer.getTime() < {maxTime}:\n'
        else:
            code = 'while continueRoutine:\n'
        buff.writeIndented(code)

        buff.setIndentLevel(1, True)
        # on each frame
        code = ('# get current time\n'
                't = {clockName}.getTime()\n'
                'tThisFlip = win.getFutureFlipTime(clock={clockName})\n'
                'tThisFlipGlobal = win.getFutureFlipTime(clock=None)\n'
                'frameN = frameN + 1  # number of completed frames '
                '(so 0 is the first frame)\n')
        buff.writeIndentedLines(code.format(clockName=self._clockName))

        # write the code for each component during frame
        buff.writeIndentedLines('# update/draw components on each frame\n')
        # just 'normal' components
        for event in self:
            if event.type == 'Static':
                continue  # we'll do those later
            event.writeFrameCode(buff)
        # update static component code last
        for event in self.getStatics():
            event.writeFrameCode(buff)

        # allow subject to quit via Esc key?
        if self.exp.settings.params['Enable Escape'].val:
            code = ('\n# check for quit (typically the Esc key)\n'
                    'if endExpNow or defaultKeyboard.getKeys(keyList=["escape"]):\n'
                    '    core.quit()\n')
            buff.writeIndentedLines(code)

        # are we done yet?
        code = (
            '\n# check if all components have finished\n'
            'if not continueRoutine:  # a component has requested a '
            'forced-end of Routine\n'
            '    routineForceEnded = True\n'
            '    break\n'
            'continueRoutine = False  # will revert to True if at least '
            'one component still running\n'
            'for thisComponent in %sComponents:\n'
            '    if hasattr(thisComponent, "status") and '
            'thisComponent.status != FINISHED:\n'
            '        continueRoutine = True\n'
            '        break  # at least one component has not yet finished\n')
        buff.writeIndentedLines(code % self.name)

        # update screen
        code = ('\n# refresh the screen\n'
                "if continueRoutine:  # don't flip if this routine is over "
                "or we'll get a blank screen\n"
                '    win.flip()\n')
        buff.writeIndentedLines(code)

        # that's done decrement indent to end loop
        buff.setIndentLevel(-1, True)

        # write the code for each component for the end of the routine
        code = ('\n# --- Ending Routine "%s" ---\n'
                'for thisComponent in %sComponents:\n'
                '    if hasattr(thisComponent, "setAutoDraw"):\n'
                '        thisComponent.setAutoDraw(False)\n')
        buff.writeIndentedLines(code % (self.name, self.name))
        for event in self:
            event.writeRoutineEndCode(buff)

        if useNonSlip:
            code = (
                "# using non-slip timing so subtract the expected duration of this Routine (unless ended on request)\n"
                "if routineForceEnded:\n"
                "    routineTimer.reset()\n"
                "else:\n"
                "    routineTimer.addTime(-%f)\n"
            )
            buff.writeIndentedLines(code % (maxTime))

    def writeRoutineBeginCodeJS(self, buff, modular):

        # create the frame loop for this routine

        code = ("\nfunction %(name)sRoutineBegin(snapshot) {\n" % self.params)
        buff.writeIndentedLines(code)
        buff.setIndentLevel(1, relative=True)
        buff.writeIndentedLines("return async function () {\n")
        buff.setIndentLevel(1, relative=True)

        code = ("TrialHandler.fromSnapshot(snapshot); // ensure that .thisN vals are up to date\n\n"
                "//--- Prepare to start Routine '%(name)s' ---\n"
                "t = 0;\n"
                "%(name)sClock.reset(); // clock\n"
                "frameN = -1;\n"
                "continueRoutine = true; // until we're told otherwise\n"
                % self.params)
        buff.writeIndentedLines(code)
        # can we use non-slip timing?
        maxTime, useNonSlip = self.getMaxTime()
        if useNonSlip:
            buff.writeIndented('routineTimer.add(%f);\n' % (maxTime))

        code = "// update component parameters for each repeat\n"
        buff.writeIndentedLines(code)
        # This is the beginning of the routine, before the loop starts
        for thisCompon in self:
            if "PsychoJS" in thisCompon.targets:
                thisCompon.writeRoutineStartCodeJS(buff)

        code = ("// keep track of which components have finished\n"
                "%(name)sComponents = [];\n" % self.params)
        buff.writeIndentedLines(code)
        for thisCompon in self:
            if (('startType' in thisCompon.params) and ("PsychoJS" in thisCompon.targets)):
                code = ("%sComponents.push(%s);\n" % (self.name, thisCompon.params['name']))
                buff.writeIndentedLines(code)

        if modular:
            code = ("\nfor (const thisComponent of %(name)sComponents)\n"
                    "  if ('status' in thisComponent)\n"
                    "    thisComponent.status = PsychoJS.Status.NOT_STARTED;\n" % self.params)
        else:
            code = ("\n%(name)sComponents.forEach( function(thisComponent) {\n"
                    "  if ('status' in thisComponent)\n"
                    "    thisComponent.status = PsychoJS.Status.NOT_STARTED;\n"
                    "   });\n" % self.params)
        buff.writeIndentedLines(code)

        # are we done yet?
        code = ("return Scheduler.Event.NEXT;\n")
        buff.writeIndentedLines(code)

        buff.setIndentLevel(-1, relative=True)
        buff.writeIndentedLines("}\n")
        buff.setIndentLevel(-1, relative=True)
        buff.writeIndentedLines("}\n")

    def writeEachFrameCodeJS(self, buff, modular):
        # can we use non-slip timing?
        maxTime, useNonSlip = self.getMaxTime()

        # write code for each frame

        code = ("\nfunction %(name)sRoutineEachFrame() {\n" % self.params)
        buff.writeIndentedLines(code)
        buff.setIndentLevel(1, relative=True)
        buff.writeIndentedLines("return async function () {\n")
        buff.setIndentLevel(1, relative=True)

        code = ("//--- Loop for each frame of Routine '%(name)s' ---\n"
                "// get current time\n"
                "t = %(name)sClock.getTime();\n"
                "frameN = frameN + 1;"
                "// number of completed frames (so 0 is the first frame)\n" % self.params)
        buff.writeIndentedLines(code)
        # write the code for each component during frame
        buff.writeIndentedLines('// update/draw components on each frame\n')
        # just 'normal' components
        for comp in self:
            if "PsychoJS" in comp.targets and comp.type != 'Static':
                comp.writeFrameCodeJS(buff)
        # update static component code last
        for comp in self.getStatics():
            if "PsychoJS" in comp.targets:
                comp.writeFrameCodeJS(buff)

        if self.exp.settings.params['Enable Escape'].val:
            code = ("// check for quit (typically the Esc key)\n"
                    "if (psychoJS.experiment.experimentEnded || psychoJS.eventManager.getKeys({keyList:['escape']}).length > 0) {\n"
                    "  return quitPsychoJS('The [Escape] key was pressed. Goodbye!', false);\n"
                    "}\n\n")
            buff.writeIndentedLines(code)

        # are we done yet?
        code = ("// check if the Routine should terminate\n"
                "if (!continueRoutine) {"
                "  // a component has requested a forced-end of Routine\n"
                "  return Scheduler.Event.NEXT;\n"
                "}\n\n"
                "continueRoutine = false;  "
                "// reverts to True if at least one component still running\n")
        buff.writeIndentedLines(code)

        if modular:
            code = ("for (const thisComponent of %(name)sComponents)\n"
                    "  if ('status' in thisComponent && thisComponent.status !== PsychoJS.Status.FINISHED) {\n"
                    "    continueRoutine = true;\n"
                    "    break;\n"
                    "  }\n")
        else:
            code = ("%(name)sComponents.forEach( function(thisComponent) {\n"
                    "  if ('status' in thisComponent && thisComponent.status !== PsychoJS.Status.FINISHED) {\n"
                    "    continueRoutine = true;\n"
                    "  }\n"
                    "});\n")
        buff.writeIndentedLines(code % self.params)

        buff.writeIndentedLines("\n// refresh the screen if continuing\n")
        if useNonSlip:
            buff.writeIndentedLines("if (continueRoutine "
                                    "&& routineTimer.getTime() > 0) {")
        else:
            buff.writeIndentedLines("if (continueRoutine) {")
        code = ("  return Scheduler.Event.FLIP_REPEAT;\n"
                "} else {\n"
                "  return Scheduler.Event.NEXT;\n"
                "}\n")
        buff.writeIndentedLines(code)
        buff.setIndentLevel(-1, relative=True)
        buff.writeIndentedLines("};\n")
        buff.setIndentLevel(-1, relative=True)
        buff.writeIndentedLines("}\n")

    def writeRoutineEndCode(self, buff):
        # can we use non-slip timing?
        maxTime, useNonSlip = self.getMaxTime()

        # reset routineTimer at the *very end* of all non-nonSlip routines
        if not useNonSlip:
            code = ('# the Routine "%s" was not non-slip safe, so reset '
                    'the non-slip timer\n'
                    'routineTimer.reset()\n')
            buff.writeIndentedLines(code % self.name)


    def writeRoutineEndCodeJS(self, buff, modular):
        # can we use non-slip timing?
        maxTime, useNonSlip = self.getMaxTime()

        code = ("\nfunction %(name)sRoutineEnd(snapshot) {\n" % self.params)
        buff.writeIndentedLines(code)
        buff.setIndentLevel(1, relative=True)
        buff.writeIndentedLines("return async function () {\n")
        buff.setIndentLevel(1, relative=True)

        if modular:
            code = ("//--- Ending Routine '%(name)s' ---\n"
                    "for (const thisComponent of %(name)sComponents) {\n"
                    "  if (typeof thisComponent.setAutoDraw === 'function') {\n"
                    "    thisComponent.setAutoDraw(false);\n"
                    "  }\n"
                    "}\n")
        else:
            code = ("//--- Ending Routine '%(name)s' ---\n"
                    "%(name)sComponents.forEach( function(thisComponent) {\n"
                    "  if (typeof thisComponent.setAutoDraw === 'function') {\n"
                    "    thisComponent.setAutoDraw(false);\n"
                    "  }\n"
                    "});\n")
        buff.writeIndentedLines(code  % self.params)
        # add the EndRoutine code for each component
        for compon in self:
            if "PsychoJS" in compon.targets:
                compon.writeRoutineEndCodeJS(buff)

        # reset routineTimer at the *very end* of all non-nonSlip routines
        if not useNonSlip:
            code = ('// the Routine "%s" was not non-slip safe, so reset '
                    'the non-slip timer\n'
                    'routineTimer.reset();\n\n')
            buff.writeIndentedLines(code % self.name)

        buff.writeIndentedLines(
            "// Routines running outside a loop should always advance the datafile row\n"
            "if (currentLoop === psychoJS.experiment) {\n"
            "  psychoJS.experiment.nextEntry(snapshot);\n"
            "}\n")
        buff.writeIndented('return Scheduler.Event.NEXT;\n')
        buff.setIndentLevel(-1, relative=True)
        buff.writeIndentedLines("}\n")
        buff.setIndentLevel(-1, relative=True)
        buff.writeIndentedLines("}\n")

    def writeExperimentEndCode(self, buff):
        """Some components have
        """
        # This is the beginning of the routine, before the loop starts
        for component in self:
            component.writeExperimentEndCode(buff)

    def writeExperimentEndCodeJS(self, buff):
        """This defines the code for the frames of a single routine
        """
        # This is the beginning of the routine, before the loop starts
        for component in self:
            if 'writeExperimentEndCodeJS' in dir(component):
                component.writeExperimentEndCodeJS(buff)

    def getType(self):
        return 'Routine'

    def getComponentFromName(self, name):
        for comp in self:
            if comp.params['name'].val == name:
                return comp
        return None

    def getComponentFromType(self, thisType):
        for comp in self:
            if comp.type == thisType:
                return comp
        return None

    def hasOnlyStaticComp(self):
        return all([comp.type == 'Static' for comp in self])

    def getMaxTime(self):
        """What the last (predetermined) stimulus time to be presented. If
        there are no components or they have code-based times then will
        default to 10secs
        """
        maxTime = 0
        nonSlipSafe = True  # if possible
        for component in self:
            if 'startType' in component.params:
                start, duration, nonSlip = component.getStartAndDuration()
                if not nonSlip:
                    nonSlipSafe = False
                if duration == FOREVER:
                    # only the *start* of an unlimited event should contribute
                    # to maxTime
                    duration = 1  # plus some minimal duration so it's visible
                # now see if we have a end t value that beats the previous max
                try:
                    # will fail if either value is not defined:
                    thisT = start + duration
                except Exception:
                    thisT = 0
                maxTime = max(maxTime, thisT)
        if maxTime == 0:  # if there are no components
            maxTime = 10
            nonSlipSafe = False
        return maxTime, nonSlipSafe

    @property
    def disabled(self):
        return bool(self.params['disabled'])

    @disabled.setter
    def disabled(self, value):
        self.params['disabled'].val = value
