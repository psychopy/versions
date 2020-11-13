#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Part of the PsychoPy library
# Copyright (C) 2002-2018 Jonathan Peirce (C) 2019-2020 Open Science Tools Ltd.
# Distributed under the terms of the GNU General Public License (GPL).

"""Describes the Flow of an experiment
"""

from __future__ import absolute_import, print_function
from past.builtins import basestring

from psychopy.experiment.routine import Routine
from psychopy.experiment.loops import LoopTerminator, LoopInitiator


class Flow(list):
    """The flow of the experiment is a list of L{Routine}s, L{LoopInitiator}s
    and L{LoopTerminator}s, that will define the order in which events occur
    """

    def __init__(self, exp):
        list.__init__(self)
        self.exp = exp
        self._currentRoutine = None
        self._loopList = []  # will be used while we write the code
        self._loopController = {'LoopInitiator': [],
                                'LoopTerminator': []}  # Controls whether loop is written

    @property
    def loopDict(self):
        """Creates a tree of the Flow:
        {entry:object, children:list, parent:object}
        :return:
        """
        loopDict = {}
        currentList = []
        loopStack = [currentList]
        for thisEntry in self:
            if thisEntry.getType() == 'LoopInitiator':
                currentList.append(thisEntry.loop) # this loop is child of current
                loopDict[thisEntry.loop] = []  # and is (current) empty list awaiting children
                currentList = loopDict[thisEntry.loop]
                loopStack.append(loopDict[thisEntry.loop])  # update the list of loops (for depth)
            elif thisEntry.getType() == 'LoopTerminator':
                loopStack.pop()
                currentList = loopStack[-1]
            else:
                # routines should be added to current
                currentList.append(thisEntry)
        return loopDict

    def __repr__(self):
        return "psychopy.experiment.Flow(%s)" % (str(list(self)))

    def addLoop(self, loop, startPos, endPos):
        """Adds initiator and terminator objects for the loop
        into the Flow list"""
        self.insert(int(endPos), LoopTerminator(loop))
        self.insert(int(startPos), LoopInitiator(loop))
        self.exp.requirePsychopyLibs(['data'])  # needed for TrialHandlers etc

    def addRoutine(self, newRoutine, pos):
        """Adds the routine to the Flow list"""
        self.insert(int(pos), newRoutine)

    def removeComponent(self, component, id=None):
        """Removes a Loop, LoopTerminator or Routine from the flow

        For a Loop (or initiator or terminator) to be deleted we can simply
        remove the object using normal list syntax. For a Routine there may
        be more than one instance in the Flow, so either choose which one
        by specifying the id, or all instances will be removed (suitable if
        the Routine has been deleted).
        """
        if component.getType() in ['LoopInitiator', 'LoopTerminator']:
            component = component.loop  # and then continue to do the next
        handlers = ('StairHandler', 'TrialHandler', 'MultiStairHandler')
        if component.getType() in handlers:
            # we need to remove the loop's termination points
            toBeRemoved = []
            for comp in self:
                # bad to change the contents of self when looping through self
                if comp.getType() in ['LoopInitiator', 'LoopTerminator']:
                    if comp.loop == component:
                        # self.remove(comp) --> skips over loop terminator if
                        # its an empty loop
                        toBeRemoved.append(comp)
            for comp in toBeRemoved:
                self.remove(comp)
        elif component.getType() == 'Routine':
            if id is None:
                # a Routine may come up multiple times - remove them all
                # self.remove(component)  # cant do this - two empty routines
                # (with diff names) look the same to list comparison
                toBeRemoved = []
                for id, compInFlow in enumerate(self):
                    if (hasattr(compInFlow, 'name') and
                            component.name == compInFlow.name):
                        toBeRemoved.append(id)
                # need to delete from the end backwards or the order changes
                toBeRemoved.reverse()
                for id in toBeRemoved:
                    del self[id]
            else:
                # just delete the single entry we were given (e.g. from
                # right-click in GUI)
                del self[id]


    def integrityCheck(self):
        """Check that the flow makes sense together and check each component"""

        # force monitor to reload for checks (ie. in case monitor has changed)
        self.exp.settings._monitor = None

        # No checks currently made on flow itself

        trailingWhitespace = []
        constWarnings = []
        for entry in self:
            if hasattr(entry, "integrityCheck"):
                entry.integrityCheck()
            # Now check each routine/loop
            # NB each entry is a routine or LoopInitiator/Terminator
            if not isinstance(entry, Routine):
                continue

            # TODO: the following tests of dubiousConstantUpdates should be
            #  moved into the alerts mechanism under the comp.integrityCheck()
            for component in entry:
                # detect and strip trailing whitespace (can cause problems):
                for key in component.params:
                    field = component.params[key]
                    if not hasattr(field, 'label'):
                        continue  # no problem, no warning
                    if (field.label.lower() in ['text', 'customize'] or
                            not field.valType in ('str', 'code')):
                        continue
                    if (isinstance(field.val, basestring) and
                            field.val != field.val.strip()):
                        trailingWhitespace.append(
                            (field.val, key, component, entry))
                        field.val = field.val.strip()
                # detect 'constant update' fields that seem intended to be
                # dynamic:
                for field, key in component._dubiousConstantUpdates():
                    if field:
                        constWarnings.append(
                            (field.val, key, component, entry))

        if trailingWhitespace:
            warnings = []
            msg = '"%s", in Routine %s (%s: %s)'
            for field, key, component, routine in trailingWhitespace:
                vals = (field, routine.params['name'],
                        component.params['name'], key.capitalize())
                warnings.append(msg % vals)
            print('Note: Trailing white-space removed:\n ', end='')
            # non-redundant, order unknown
            print('\n  '.join(list(set(warnings))))
        if constWarnings:
            warnings = []
            msg = '"%s", in Routine %s (%s: %s)'
            for field, key, component, routine in constWarnings:
                vals = (field, routine.params['name'],
                        component.params['name'], key.capitalize())
                warnings.append(msg % vals)
            print('Note: Dynamic code seems intended but updating '
                  'is "constant":\n ', end='')
            # non-redundant, order unknown
            print('\n  '.join(list(set(warnings))))

    def writePreCode(self,script):
        """Write the code that comes before the Window is created
        """
        script.writeIndentedLines("\n# Start Code - component code to be "
                                  "run before the window creation\n")
        for entry in self:
            # NB each entry is a routine or LoopInitiator/Terminator
            self._currentRoutine = entry
            # very few components need writeStartCode:
            if hasattr(entry, 'writePreCode'):
                entry.writePreCode(script)

    def writeStartCode(self, script):
        """Write the code that comes after the Window is created
        """
        script.writeIndentedLines("\n# Start Code - component code to be "
                                  "run after the window creation\n")
        for entry in self:
            # NB each entry is a routine or LoopInitiator/Terminator
            self._currentRoutine = entry
            # very few components need writeStartCode:
            if hasattr(entry, 'writeStartCode'):
                entry.writeStartCode(script)

    def writeBody(self, script):
        """Write the rest of the code
        """
        # writeStartCode and writeInitCode:
        for entry in self:
            # NB each entry is a routine or LoopInitiator/Terminator
            self._currentRoutine = entry
            entry.writeInitCode(script)
        # create clocks (after initialising stimuli)
        code = ("\n# Create some handy timers\n"
                "globalClock = core.Clock()  # to track the "
                "time since experiment started\n"
                "routineTimer = core.CountdownTimer()  # to "
                "track time remaining of each (non-slip) routine \n")
        script.writeIndentedLines(code)
        # run-time code
        for entry in self:
            self._currentRoutine = entry
            entry.writeMainCode(script)
        # tear-down code (very few components need this)
        for entry in self:
            self._currentRoutine = entry
            entry.writeExperimentEndCode(script)


    def writeFlowSchedulerJS(self, script):
        """Initialise each component and then write the per-frame code too
        """

        # handle email for error messages
        if 'email' in self.exp.settings.params and self.exp.settings.params['email'].val:
            code = ("// If there is an error, we should inform the participant and email the experimenter\n"
                    "// note: we use window.onerror rather than a try/catch as the latter\n"
                    "// do not handle so well exceptions thrown asynchronously\n"
                    "/*window.onerror = function(message, source, lineno, colno, error) {\n"
                    "  console.error(error);\n"
                    "  psychoJS.gui.dialog({'error' : error});\n"
                    "  //psychoJS.core.sendErrorToExperimenter(exception);\n"
                    "  // show error stack on console:\n"
                    "  var json = JSON.parse(error);\n"
                    "  console.error(json.stack);\n"
                    "  return true;\n"
                    "}*/\n")
            script.writeIndentedLines(code)

        code = ("// schedule the experiment:\n"
                "psychoJS.schedule(psychoJS.gui.DlgFromDict({\n"
                "  dictionary: expInfo,\n"
                "  title: expName\n}));\n"
                "\n"
                "const flowScheduler = new Scheduler(psychoJS);\n"
                "const dialogCancelScheduler = new Scheduler(psychoJS);\n"
                "psychoJS.scheduleCondition(function() { return (psychoJS.gui.dialogComponent.button === 'OK'); }, flowScheduler, dialogCancelScheduler);\n"
                "\n")
        script.writeIndentedLines(code)

        code = ("// flowScheduler gets run if the participants presses OK\n"
               "flowScheduler.add(updateInfo); // add timeStamp\n"
               "flowScheduler.add(experimentInit);\n")
        script.writeIndentedLines(code)
        loopStack = []
        for thisEntry in self:
            if not loopStack:  # if not currently in a loop
                if thisEntry.getType() == 'LoopInitiator':
                    code = ("const {name}LoopScheduler = new Scheduler(psychoJS);\n"
                            "flowScheduler.add({name}LoopBegin, {name}LoopScheduler);\n"
                            "flowScheduler.add({name}LoopScheduler);\n"
                            "flowScheduler.add({name}LoopEnd);\n"
                            .format(name=thisEntry.loop.params['name'].val))
                    loopStack.append(thisEntry.loop)
                elif thisEntry.getType() == "Routine":
                    code = ("flowScheduler.add({params[name]}RoutineBegin());\n"
                            "flowScheduler.add({params[name]}RoutineEachFrame());\n"
                            "flowScheduler.add({params[name]}RoutineEnd());\n"
                            .format(params=thisEntry.params))
            else:  # we are already in a loop so don't code here just count
                code = ""
                if thisEntry.getType() == 'LoopInitiator':
                    loopStack.append(thisEntry.loop)
                elif thisEntry.getType() == 'LoopTerminator':
                    loopStack.remove(thisEntry.loop)
            script.writeIndentedLines(code)
        # quit when all routines are finished
        script.writeIndented("flowScheduler.add(quitPsychoJS, '', true);\n")
        # handled all the flow entries
        code = ("\n// quit if user presses Cancel in dialog box:\n"
                "dialogCancelScheduler.add(quitPsychoJS, '', false);\n\n")
        script.writeIndentedLines(code)

        # Write resource list
        resourceFiles = set([resource['rel'].replace("\\", "/") for resource in self.exp.getResourceFiles()])
        if self.exp.htmlFolder:
            resourceFolderStr = "resources/"
        else:
            resourceFolderStr = ""
        script.writeIndented("psychoJS.start({\n")
        script.setIndentLevel(1, relative=True)
        script.writeIndentedLines("expName: expName,\n"
                                  "expInfo: expInfo,\n")
        # if we have an html folder then we moved files there so just use that
        # if not, then we'll need to list all known resource files
        if not self.exp.htmlFolder:
            script.writeIndentedLines("resources: [\n")
            script.setIndentLevel(1, relative=True)
            code = ""
            for idx, resource in enumerate(resourceFiles):
                temp = "{{'name': '{0}', 'path': '{1}{0}'}}".format(resource, resourceFolderStr)
                code += temp
                if idx != (len(resourceFiles)-1):
                    code += ",\n"  # Trailing comma
            script.writeIndentedLines(code)
            script.setIndentLevel(-1, relative=True)
            script.writeIndented("]\n")
            script.setIndentLevel(-1, relative=True)
        script.writeIndented("});\n\n")

    def writeLoopHandlerJS(self, script, modular):
        """
        Function for setting up handler to look after randomisation of conditions etc
        """
        # Then on the flow we need only the Loop Init/terminate
        for entry in self:
            loopType = entry.getType()  # Get type i.e., routine or loop
            if loopType in self._loopController:
                loopName = entry.loop.params['name'].val  # Get loop name
                if loopName not in self._loopController[loopType]:  # Write if not already written
                    entry.writeMainCodeJS(script, modular)  # will either be function trialsBegin() or trialsEnd()
                    self._loopController[loopType].append(loopName)

    def _resetLoopController(self):
        """Resets _loopController so loops are written on each call to write script"""
        self._loopController = {'LoopInitiator': [],
                                'LoopTerminator': []}  # Controls whether loop is written
