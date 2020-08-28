#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Part of the PsychoPy library
# Copyright (C) 2002-2018 Jonathan Peirce (C) 2019-2020 Open Science Tools Ltd.
# Distributed under the terms of the GNU General Public License (GPL).

import io
import sys
import os
import argparse
import traceback
from copy import deepcopy
from subprocess import PIPE, Popen

from psychopy.constants import PY3
from psychopy import __version__, logging

# parse args for subprocess
parser = argparse.ArgumentParser(description='Compile your python file from here')
parser.add_argument('infile', help='The input (psyexp) file to be compiled')
parser.add_argument('--version', '-v', help='The PsychoPy version to use for compiling the script. e.g. 1.84.1')
parser.add_argument('--outfile', '-o', help='The output (py) file to be generated (defaults to the ')


def generateScript(experimentPath, exp, target="PsychoPy"):
    """
    Generate python script from the current builder experiment.

    Parameters
    ----------
    experimentPath: str
        Experiment path and filename
    exp: experiment.Experiment object
        The current PsychoPy experiment object generated using Builder
    target: str
        PsychoPy or PsychoJS - determines whether Python or JS script is generated.

    Returns
    -------
    """
    print("Generating {} script...\n".format(target))
    exp.expPath = os.path.abspath(experimentPath)

    if sys.platform == 'win32':  # get name of executable
        pythonExec = sys.executable
    else:
        pythonExec = sys.executable.replace(' ', '\ ')

    filename = experimentPath
    if not PY3:  # encode path in Python2
        filename = experimentPath = experimentPath.encode(sys.getfilesystemencoding())

    # Compile script from command line using version
    compiler = 'psychopy.scripts.psyexpCompile'
    # run compile
    cmd = [pythonExec, '-m', compiler, exp.filename,
           '-o', experimentPath]
    # if version is not specified then don't touch useVersion at all
    version = exp.settings.params['Use version'].val

    if version not in [None, 'None', '', __version__]:
        cmd.extend(['-v', version])
        logging.info(' '.join(cmd))
        output = Popen(cmd,
                       stdout=PIPE,
                       stderr=PIPE,
                       universal_newlines=True)
        stdout, stderr = output.communicate()
        sys.stdout.write(stdout)
        sys.stderr.write(stderr)
    else:
        compileScript(infile=exp, version=None, outfile=filename)

def compileScript(infile=None, version=None, outfile=None):
    """
    Compile either Python or JS PsychoPy script from .psyexp file.

    Paramaters
    ----------

    infile: string, experiment.Experiment object
        The input (psyexp) file to be compiled
    version: str
        The PsychoPy version to use for compiling the script. e.g. 1.84.1.
        Warning: Cannot set version if module imported. Set version from
        command line interface only.
    outfile: string
        The output file to be generated (defaults to Python script).
    """
    def _setVersion(version):
        """
        Sets the version to be used for compiling using the useVersion function

        Parameters
        ----------
        version: string
            The version requested
        """

        # Set version
        if version:
            from psychopy import useVersion
            useVersion(version)

        global logging

        from psychopy import logging

        if __name__ != '__main__' and version not in [None, 'None', 'none', '']:
            version = None
            msg = "You cannot set version by calling compileScript() manually. Setting 'version' to None."
            logging.warning(msg)

        return version

    def _getExperiment(infile, version):
        """
        Get experiment if infile is not type experiment.Experiment.

        Parameters
        ----------
        infile: string, experiment.Experiment object
            The input (psyexp) file to be compiled
        version: string
            The version requested
        Returns
        -------
        experiment.Experiment
            The experiment object used for generating the experiment script
        """
        # import PsychoPy experiment and write script with useVersion active
        from psychopy.app.builder import experiment
        # Check infile type
        if isinstance(infile, experiment.Experiment):
            thisExp = infile
        else:
            thisExp = experiment.Experiment()
            thisExp.loadFromXML(infile)
            thisExp.psychopyVersion = version

        return thisExp

    def _removeDisabledComponents(exp):
        """
        Drop disabled components, if any.

        Parameters
        ---------
        exp : psychopy.experiment.Experiment
            The experiment from which to remove all components that have been
            marked `disabled`.

        Returns
        -------
        exp : psychopy.experiment.Experiment
            The experiment with the disabled components removed.

        Notes
        -----
        This function leaves the original experiment unchanged as it always
        only works on (and returns) a copy.
        """
        # Leave original experiment unchanged.
        exp = deepcopy(exp)

        for _, routine in list(exp.routines.items()):  # PY2/3 compat
            for component in routine:
                try:
                    if component.params['disabled'].val:
                        routine.removeComponent(component)
                except KeyError:
                    pass

        return exp

    def _setTarget(outfile):
        """
        Set target for compiling i.e., Python or JavaScript.

        Parameters
        ----------
        outfile : string
             The output file to be generated (defaults to Python script).
        Returns
        -------
        string
            The Python or JavaScript target type
        """
        # Set output type, either JS or Python
        if outfile.endswith(".js"):
            targetOutput = "PsychoJS"
        else:
            targetOutput = "PsychoPy"

        return targetOutput

    def _makeTarget(thisExp, outfile, targetOutput):
        """
        Generate the actual scripts for Python and/or JS.

        Parameters
        ----------
        thisExp : experiment.Experiment object
            The current experiment created under requested version
        outfile : string
             The output file to be generated (defaults to Python script).
        targetOutput : string
            The Python or JavaScript target type
        """
        # Write script
        if targetOutput == "PsychoJS":
            # Write module JS code
            script = thisExp.writeScript(outfile, target=targetOutput, modular=True)
            # Write no module JS code
            outfileNoModule = outfile.replace('.js', '-legacy-browsers.js')  # For no JS module script
            scriptNoModule = thisExp.writeScript(outfileNoModule, target=targetOutput, modular=False)
            # Store scripts in list
            scriptDict = {'outfile': script, 'outfileNoModule': scriptNoModule}
        else:
            script = thisExp.writeScript(outfile, target=targetOutput)
            scriptDict = {'outfile': script}

        # Output script to file
        for scripts in scriptDict:
            if not type(scriptDict[scripts]) in (str, type(u'')):
                # We have a stringBuffer not plain string/text
                scriptText = scriptDict[scripts].getvalue()
            else:
                # We already have the text
                scriptText = scriptDict[scripts]
            with io.open(eval(scripts), 'w', encoding='utf-8-sig') as f:
                f.write(scriptText)

        return 1

    ###### Write script #####
    version = _setVersion(version)
    thisExp = _getExperiment(infile, version)
    thisExp = _removeDisabledComponents(thisExp)
    targetOutput = _setTarget(outfile)
    _makeTarget(thisExp, outfile, targetOutput)


if __name__ == "__main__":
    # define args
    args = parser.parse_args()
    if args.outfile is None:
        args.outfile = args.infile.replace(".psyexp", ".py")
    compileScript(args.infile, args.version, args.outfile)
