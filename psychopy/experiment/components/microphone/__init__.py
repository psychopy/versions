#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Part of the PsychoPy library
# Copyright (C) 2002-2018 Jonathan Peirce (C) 2019-2022 Open Science Tools Ltd.
# Distributed under the terms of the GNU General Public License (GPL).

# Author: Jeremy R. Gray, 2012
from pathlib import Path

from psychopy.alerts import alert
from psychopy.experiment.components import BaseComponent, Param, getInitVals, _translate
from psychopy.sound.microphone import Microphone, _hasPTB
from psychopy.sound.audiodevice import sampleRateQualityLevels
from psychopy.sound.audioclip import AUDIO_SUPPORTED_CODECS
from psychopy.localization import _localized as __localized

_localized = __localized.copy()
_localized.update({'stereo': _translate('Stereo'),
                   'channel': _translate('Channel')})
from psychopy.tests import _vmTesting

if _hasPTB and not _vmTesting:
    devices = {d.deviceName: d for d in Microphone.getDevices()}
else:
    devices = {}
sampleRates = {r[1]: r[0] for r in sampleRateQualityLevels.values()}
devices['default'] = None

onlineTranscribers = {
    "Google": "GOOGLE"
}
localTranscribers = {
    "Google": "google",
    "Built-in": "sphinx"
}
allTranscribers = {**localTranscribers, **onlineTranscribers}


class MicrophoneComponent(BaseComponent):
    """An event class for capturing short sound stimuli"""
    categories = ['Responses']
    targets = ['PsychoPy', 'PsychoJS']
    iconFile = Path(__file__).parent / 'microphone.png'
    tooltip = _translate('Microphone: basic sound capture (fixed onset & '
                         'duration), okay for spoken words')

    def __init__(self, exp, parentName, name='mic',
                 startType='time (s)', startVal=0.0,
                 stopType='duration (s)', stopVal=2.0,
                 startEstim='', durationEstim='',
                 channels='auto', device="default",
                 sampleRate='DVD Audio (48kHz)', maxSize=24000,
                 outputType='default', speakTimes=True, trimSilent=False,
                 transcribe=True, transcribeBackend="Google", transcribeLang="en-US", transcribeWords="",
                 #legacy
                 stereo=None, channel=None):
        super(MicrophoneComponent, self).__init__(
            exp, parentName, name=name,
            startType=startType, startVal=startVal,
            stopType=stopType, stopVal=stopVal,
            startEstim=startEstim, durationEstim=durationEstim)

        self.type = 'Microphone'
        self.url = "https://www.psychopy.org/builder/components/microphone.html"
        self.exp.requirePsychopyLibs(['sound'])

        self.order += []

        self.params['stopType'].allowedVals = ['duration (s)']
        msg = _translate(
            'The duration of the recording in seconds; blank = 0 sec')
        self.params['stopType'].hint = msg

        # params
        msg = _translate("What microphone device would you like the use to record? This will only affect local "
                         "experiments - online experiments ask the participant which mic to use.")
        self.params['device'] = Param(
            device, valType='str', inputType="choice", categ="Basic",
            allowedVals=list(devices),
            hint=msg,
            label=_translate("Device")
        )

        msg = _translate(
            "Record two channels (stereo) or one (mono, smaller file). Select 'auto' to use as many channels "
            "as the selected device allows.")
        if stereo is not None:
            # If using a legacy mic component, work out channels from old bool value of stereo
            channels = ['mono', 'stereo'][stereo]
        self.params['channels'] = Param(
            channels, valType='str', inputType="choice", categ='Hardware',
            allowedVals=['auto', 'mono', 'stereo'],
            hint=msg,
            label=_translate('Channels'))

        msg = _translate(
            "How many samples per second (Hz) to record at")
        self.params['sampleRate'] = Param(
            sampleRate, valType='num', inputType="choice", categ='Hardware',
            allowedVals=list(sampleRates),
            hint=msg, direct=False,
            label=_translate('Sample Rate (Hz)'))

        msg = _translate(
            "To avoid excessively large output files, what is the biggest file size you are likely to expect?")
        self.params['maxSize'] = Param(
            maxSize, valType='num', inputType="single", categ='Hardware',
            hint=msg,
            label=_translate('Max Recording Size (kb)'))

        msg = _translate(
            "What file type should output audio files be saved as?")
        self.params['outputType'] = Param(
            outputType, valType='code', inputType='choice', categ='Data',
            allowedVals=["default"] + AUDIO_SUPPORTED_CODECS,
            hint=msg,
            label=_translate("Output File Type")
        )

        msg = _translate(
            "Tick this to save times when the participant starts and stops speaking")
        self.params['speakTimes'] = Param(
            speakTimes, valType='bool', inputType='bool', categ='Data',
            hint=msg,
            label=_translate("Speaking Start / Stop Times")
        )

        msg = _translate(
            "Trim periods of silence from the output file")
        self.params['trimSilent'] = Param(
            trimSilent, valType='bool', inputType='bool', categ='Data',
            hint=msg,
            label=_translate("Trim Silent")
        )

        # Transcription params
        self.order += [
            'transcribe',
            'transcribeBackend',
            'transcribeLang',
            'transcribeWords',
        ]
        self.params['transcribe'] = Param(
            transcribe, valType='bool', inputType='bool', categ='Transcription',
            hint=_translate("Whether to transcribe the audio recording and store the transcription"),
            label=_translate("Transcribe Audio")
        )

        for depParam in ['transcribeBackend', 'transcribeLang', 'transcribeWords']:
            self.depends.append({
                "dependsOn": "transcribe",
                "condition": "==True",
                "param": depParam,
                "true": "enable",  # what to do with param if condition is True
                "false": "disable",  # permitted: hide, show, enable, disable
            })

        self.params['transcribeBackend'] = Param(
            transcribeBackend, valType='code', inputType='choice', categ='Transcription',
            allowedVals=list(allTranscribers), direct=False,
            hint=_translate("What transcription service to use to transcribe audio?"),
            label=_translate("Transcription Backend")
        )

        self.params['transcribeLang'] = Param(
            transcribeLang, valType='str', inputType='single', categ='Transcription',
            hint=_translate("What language you expect the recording to be spoken in, e.g. en-US for English"),
            label=_translate("Transcription Language")
        )

        self.params['transcribeWords'] = Param(
            transcribeWords, valType='list', inputType='single', categ='Transcription',
            hint=_translate("Set list of words to listen for - if blank will listen for all words in chosen language. \n\n"
                            "If using the built-in transcriber, you can set a minimum % confidence level using a colon "
                            "after the word, e.g. 'red:100', 'green:80'. Otherwise, default confidence level is 80%."),
            label=_translate("Expected Words")
        )

    def writeStartCode(self, buff):
        inits = getInitVals(self.params)
        # Use filename with a suffix to store recordings
        code = (
            "# Make folder to store recordings from %(name)s\n"
            "%(name)sRecFolder = filename + '_%(name)s_recorded'\n"
            "if not os.path.isdir(%(name)sRecFolder):\n"
        )
        buff.writeIndentedLines(code % inits)
        buff.setIndentLevel(1, relative=True)
        code = (
                "os.mkdir(%(name)sRecFolder)\n"
        )
        buff.writeIndentedLines(code % inits)
        buff.setIndentLevel(-1, relative=True)

    def writeStartCodeJS(self, buff):
        inits = getInitVals(self.params)
        code = (
            "// Define folder to store recordings from %(name)s"
            "%(name)sRecFolder = filename + '_%(name)s_recorded"
        )
        buff.writeIndentedLines(code % inits)

    def writeInitCode(self, buff):
        inits = getInitVals(self.params)
        # Substitute sample rate value for numeric equivalent
        inits['sampleRate'] = sampleRates[inits['sampleRate'].val]
        # Substitute channel value for numeric equivalent
        inits['channels'] = {'mono': 1, 'stereo': 2, 'auto': None}[self.params['channels'].val]
        # Substitute device name for device index, or default if not found
        if self.params['device'].val in devices:
            device = devices[self.params['device'].val]
            if hasattr(device, "deviceIndex"):
                inits['device'] = device.deviceIndex
            else:
                inits['device'] = None
        else:
            alert(4330, strFields={'device': self.params['device'].val})
            inits['device'] = None
        # Create Microphone object and clips dict
        code = (
            "%(name)s = sound.microphone.Microphone(\n"
        )
        buff.writeIndentedLines(code % inits)
        buff.setIndentLevel(1, relative=True)
        code = (
                "device=%(device)s, channels=%(channels)s, \n"
                "sampleRateHz=%(sampleRate)s, maxRecordingSize=%(maxSize)s\n"
        )
        buff.writeIndentedLines(code % inits)
        buff.setIndentLevel(-1, relative=True)
        code = (
            ")\n"
        )
        buff.writeIndentedLines(code % inits)

    def writeInitCodeJS(self, buff):
        inits = getInitVals(self.params)
        inits['sampleRate'] = sampleRates[inits['sampleRate'].val]
        # Alert user if non-default value is selected for device
        if inits['device'].val != 'default':
            alert(5055, strFields={'name': inits['name'].val})
        # Write code
        code = (
            "%(name)s = new sound.Microphone({\n"
        )
        buff.writeIndentedLines(code % inits)
        buff.setIndentLevel(1, relative=True)
        code = (
                "win : psychoJS.window, \n"
                "name:'%(name)s',\n"
                "sampleRateHz : %(sampleRate)s,\n"
                "channels : %(channels)s,\n"
                "maxRecordingSize : %(maxSize)s,\n"
                "loopback : true,\n"
                "policyWhenFull : 'ignore',\n"
        )
        buff.writeIndentedLines(code % inits)
        buff.setIndentLevel(-1, relative=True)
        code = (
            "});\n"
        )
        buff.writeIndentedLines(code % inits)

    def writeFrameCode(self, buff):
        """Write the code that will be called every frame"""
        inits = getInitVals(self.params)
        inits['routine'] = self.parentName
        # Start the recording
        code = (
            "\n"
            "# %(name)s updates"
        )
        buff.writeIndentedLines(code % inits)
        self.writeStartTestCode(buff)
        code = (
                "# start recording with %(name)s\n"
                "%(name)s.start()\n"
                "%(name)s.status = STARTED\n"
        )
        buff.writeIndentedLines(code % inits)
        buff.setIndentLevel(-1, relative=True)
        # Get clip each frame
        code = (
            "if %(name)s.status == STARTED:\n"
        )
        buff.writeIndentedLines(code % inits)
        buff.setIndentLevel(1, relative=True)
        code = (
                "# update recorded clip for %(name)s\n"
                "%(name)s.poll()\n"
        )
        buff.writeIndentedLines(code % inits)
        buff.setIndentLevel(-1, relative=True)
        # Stop recording
        self.writeStopTestCode(buff)
        code = (
            "# stop recording with %(name)s\n"
            "%(name)s.stop()\n"
            "%(name)s.status = FINISHED\n"
        )
        buff.writeIndentedLines(code % inits)
        buff.setIndentLevel(-2, relative=True)

    def writeFrameCodeJS(self, buff):
        inits = getInitVals(self.params)
        inits['routine'] = self.parentName
        # Start the recording
        self.writeStartTestCodeJS(buff)
        code = (
                "await %(name)s.start();\n"
        )
        buff.writeIndentedLines(code % inits)
        buff.setIndentLevel(-1, relative=True)
        code = (
            "}"
        )
        buff.writeIndentedLines(code % inits)
        if self.params['stopVal'].val not in ['', None, -1, 'None']:
            # Stop the recording
            self.writeStopTestCodeJS(buff)
            code = (
                    "%(name)s.pause();\n"
            )
            buff.writeIndentedLines(code % inits)
            buff.setIndentLevel(-1, relative=True)
            code = (
                "}"
            )
            buff.writeIndentedLines(code % inits)

    def writeRoutineEndCode(self, buff):
        inits = getInitVals(self.params)
        # Alter inits
        if len(self.exp.flow._loopList):
            inits['loop'] = self.exp.flow._loopList[-1].params['name']
            inits['filename'] = f"'recording_{inits['name']}_{inits['loop']}_%s.{inits['outputType']}' % {inits['loop']}.thisTrialN"
        else:
            inits['loop'] = "thisExp"
            inits['filename'] = f"'recording_{inits['name']}'"
        transcribe = inits['transcribe'].val
        if inits['transcribe'].val == False:
            inits['transcribeBackend'].val = None
        if inits['outputType'].val == 'default':
            inits['outputType'].val = 'wav'
        # Warn user if their transcriber won't work locally
        if inits['transcribe'].val:
            if  inits['transcribeBackend'].val in localTranscribers:
                inits['transcribeBackend'].val = localTranscribers[self.params['transcribeBackend'].val]
            else:
                default = list(localTranscribers.values())[0]
                alert(4610, strFields={"transcriber": inits['transcribeBackend'].val, "default": default})
        # Store recordings from this routine
        code = (
            "# tell mic to keep hold of current recording in %(name)s.clips and transcript (if applicable) in %(name)s.scripts\n"
            "# this will also update %(name)s.lastClip and %(name)s.lastScript\n"
            "%(name)s.stop()\n"
        )
        buff.writeIndentedLines(code % inits)
        if inits['transcribeBackend'].val:
            code = (
                "tag = data.utils.getDateStr()\n"
                "%(name)sClip, %(name)sScript = %(name)s.bank(\n"
            )
        else:
            code = (
                "tag = data.utils.getDateStr()\n"
                "%(name)sClip = %(name)s.bank(\n"
            )
        buff.writeIndentedLines(code % inits)
        buff.setIndentLevel(1, relative=True)
        code = (
            "tag=tag, transcribe='%(transcribeBackend)s',\n"
        )
        buff.writeIndentedLines(code % inits)
        if transcribe:
            code = (
                "language=%(transcribeLang)s, expectedWords=%(transcribeWords)s\n"
            )
        else:
            code = (
                "config=None\n"
            )
        buff.writeIndentedLines(code % inits)
        buff.setIndentLevel(-1, relative=True)
        code = (
            ")\n"
            "%(loop)s.addData('%(name)s.clip', os.path.join(%(name)sRecFolder, 'recording_%(name)s_%%s.%(outputType)s' %% tag))\n"
        )
        buff.writeIndentedLines(code % inits)
        if transcribe:
            code = (
                "%(loop)s.addData('%(name)s.script', %(name)sScript)\n"
            )
            buff.writeIndentedLines(code % inits)
        # Write base end routine code
        BaseComponent.writeRoutineEndCode(self, buff)

    def writeRoutineEndCodeJS(self, buff):
        inits = getInitVals(self.params)
        inits['routine'] = self.parentName
        if inits['transcribeBackend'].val in allTranscribers:
            inits['transcribeBackend'].val = allTranscribers[self.params['transcribeBackend'].val]
        # Warn user if their transcriber won't work online
        if inits['transcribe'].val and inits['transcribeBackend'].val not in onlineTranscribers.values():
            default = list(onlineTranscribers.values())[0]
            alert(4605, strFields={"transcriber": inits['transcribeBackend'].val, "default": default})

        # Write base end routine code
        BaseComponent.writeRoutineEndCodeJS(self, buff)
        # Store recordings from this routine
        code = (
            "// stop the microphone (make the audio data ready for upload)\n"
            "await %(name)s.stop();\n"
            "// construct a filename for this recording\n"
            "thisFilename = 'recording_%(name)s_' + currentLoop.name + '_' + currentLoop.thisN\n"
            "// get the recording\n"
            "%(name)s.lastClip = await %(name)s.getRecording({\n"
        )
        buff.writeIndentedLines(code % inits)
        buff.setIndentLevel(1, relative=True)
        code = (
                "tag: thisFilename + '_' + util.MonotonicClock.getDateStr(),\n"
                "flush: false\n"
        )
        buff.writeIndentedLines(code % inits)
        buff.setIndentLevel(-1, relative=True)
        code = (
            "});\n"
            "psychoJS.experiment.addData('%(name)s.clip', thisFilename);\n"
            "// start the asynchronous upload to the server\n"
            "%(name)s.lastClip.upload();\n"
        )
        buff.writeIndentedLines(code % inits)
        if self.params['transcribe'].val:
            code = (
                "// transcribe the recording\n"
                "const transcription = await %(name)s.lastClip.transcribe({\n"
            )
            buff.writeIndentedLines(code % inits)
            buff.setIndentLevel(1, relative=True)
            code = (
                    "languageCode: %(transcribeLang)s,\n"
                    "engine: sound.AudioClip.Engine.%(transcribeBackend)s,\n"
                    "wordList: %(transcribeWords)s\n"
            )
            buff.writeIndentedLines(code % inits)
            buff.setIndentLevel(-1, relative=True)
            code = (
                "});\n"
                "%(name)s.lastScript = transcription.transcript;\n"
                "%(name)s.lastConf = transcription.confidence;\n"
                "psychoJS.experiment.addData('%(name)s.transcript', %(name)s.lastScript);\n"
                "psychoJS.experiment.addData('%(name)s.confidence', %(name)s.lastConf);\n"
            )
            buff.writeIndentedLines(code % inits)

    def writeExperimentEndCode(self, buff):
        """Write the code that will be called at the end of
        an experiment (e.g. save log files or reset hardware)
        """
        inits = getInitVals(self.params)
        if len(self.exp.flow._loopList):
            currLoop = self.exp.flow._loopList[-1]  # last (outer-most) loop
        else:
            currLoop = self.exp._expHandler
        inits['loop'] = currLoop.params['name']
        if inits['outputType'].val == 'default':
            inits['outputType'].val = 'wav'
        # Save recording
        code = (
            "# save %(name)s recordings\n"
            "for tag in %(name)s.clips:"
        )
        buff.writeIndentedLines(code % inits)
        buff.setIndentLevel(1, relative=True)
        code = (
                "for i, clip in enumerate(%(name)s.clips[tag]):\n"
        )
        buff.writeIndentedLines(code % inits)
        buff.setIndentLevel(1, relative=True)
        code = (
                    "clipFilename = 'recording_%(name)s_%%s.%(outputType)s' %% tag\n"
        )
        buff.writeIndentedLines(code % inits)
        code = (
                    "# if there's more than 1 clip with this tag, append a counter for all beyond the first\n"
                    "if i > 0:\n"
        )
        buff.writeIndentedLines(code % inits)
        buff.setIndentLevel(1, relative=True)
        code = (
                        "clipFilename += '_%%s' %% i"
        )
        buff.writeIndentedLines(code % inits)
        buff.setIndentLevel(-1, relative=True)
        code = (
                    "clip.save(os.path.join(%(name)sRecFolder, clipFilename))\n"
        )
        buff.writeIndentedLines(code % inits)
        buff.setIndentLevel(-2, relative=True)
