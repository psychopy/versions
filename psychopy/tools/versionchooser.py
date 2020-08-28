#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Part of the PsychoPy library
# Copyright (C) 2002-2018 Jonathan Peirce (C) 2019-2020 Open Science Tools Ltd.
# Distributed under the terms of the GNU General Public License (GPL).
"""PsychoPy Version Chooser to specify version within experiment scripts.
"""

from __future__ import absolute_import, print_function

import os
import sys
import subprocess  # for git commandline invocation
from subprocess import CalledProcessError
import psychopy  # for currently loaded version
from psychopy import prefs
from psychopy import logging, tools, web, constants
from pkg_resources import parse_version
if constants.PY3:
    from importlib import reload

USERDIR = prefs.paths['userPrefsDir']
VER_SUBDIR = 'versions'
VERSIONSDIR = os.path.join(USERDIR, VER_SUBDIR)

# cache because checking github for remote version tags can be slow
_localVersionsCache = []
_remoteVersionsCache = []


# ideally want localization for error messages
# but don't want to have the lib/ depend on app/, drat
# from psychopy.localization import _translate  # ideal
def _translate(string):
    """placeholder (non)function
    """
    return string


def useVersion(requestedVersion):
    """Manage paths and checkout psychopy libraries for requested versions
    of PsychoPy.

    requestedVersion :
        A string with the requested version of PsychoPy to be used.

        Can be major.minor.patch, e.g., '1.83.01', or a partial version,
        such as '1.81', or even '1'; uses the most
        recent version within that series.

        'latest' means the most recent release having a tag on github.

    returns:
        Returns the current (new) version if it was successfully loaded.
        Raises a RuntimeError if git is needed and not present, or if
        other PsychoPy modules have already been loaded. Raises a
        subprocess CalledProcessError if an invalid git tag/version was
        checked out.

    Usage (at the top of an experiment script):

        from psychopy import useVersion
        useVersion('1.80')
        from psychopy import visual, event, ...

    See also:
        ensureMinimal()
    """
    # Sanity Checks
    imported = _psychopyComponentsImported()
    if imported:
        msg = _translate("Please request a version before importing any "
                         "PsychoPy modules. (Found: {})")
        raise RuntimeError(msg.format(imported))

    # Get a proper full-version tag from a partial tag:
    reqdMajorMinorPatch = fullVersion(requestedVersion)
    logging.exp('Requested: useVersion({}) = {}'.format(requestedVersion,
                                                        reqdMajorMinorPatch))
    if not reqdMajorMinorPatch:
        msg = _translate('Unknown version `{}`')
        raise ValueError(msg.format(requestedVersion))

    if not os.path.isdir(VERSIONSDIR):
        _clone(requestedVersion)  # Allow the versions subdirectory to be built

    if constants.PY3:
        py3Compatible = _versionFilter(versionOptions(local=False), None)
        py3Compatible += _versionFilter(availableVersions(local=False), None)
        py3Compatible.sort(reverse=True)

        if reqdMajorMinorPatch not in py3Compatible:
            msg = _translate("Please request a version of PsychoPy that is compatible with Python 3. "
                             "You can choose from the following versions: {}. "
                             "Alternatively, run a Python 2 installation of PsychoPy < v1.9.0.\n")
            logging.error(msg.format(py3Compatible))
            return

    if psychopy.__version__ != reqdMajorMinorPatch:
        # Switching required, so make sure `git` is available.
        if not _gitPresent():
            msg = _translate("Please install git; needed by useVersion()")
            raise RuntimeError(msg)

        # Setup Requested Version
        _switchToVersion(reqdMajorMinorPatch)

        # Reload!
        reload(psychopy)
        reload(logging)
        reload(web)
        if _versionTuple(reqdMajorMinorPatch) >= (1, 80):
            reload(tools)  # because this file is within tools

        # TODO check for other submodules that have already been imported

    logging.exp('Version now set to: {}'.format(psychopy.__version__))
    return psychopy.__version__


def ensureMinimal(requiredVersion):
    """Raise a RuntimeError if the current version < `requiredVersion`.

    See also: useVersion()
    """
    if _versionTuple(psychopy.__version__) < _versionTuple(requiredVersion):
        msg = _translate('Required minimal version `{}` not met ({}).')
        raise RuntimeError(msg.format(requiredVersion, psychopy.__version__))
    return psychopy.__version__


def _versionTuple(versionStr):
    """Returns a tuple of int's (1, 81, 3) from a string version '1.81.03'

    Tuples allow safe version comparisons (unlike strings).
    """
    try:
        v = (versionStr.strip('.') + '.0.0.0').split('.')[:3]
    except (AttributeError, ValueError):
        raise ValueError('Bad version string: `{}`'.format(versionStr))
    return int(v[0]), int(v[1]), int(v[2])


def _switchToVersion(requestedVersion):
    """Checkout (or clone then checkout) the requested version, set sys.path
    so that the new version will be found when import is called. Upon exit,
    the checked out version remains checked out, but the sys.path reverts.

    NB When installed with pip/easy_install PsychoPy will live in
    a site-packages directory, which should *not* be removed as it may
    contain other relevant and needed packages.
    """

    if not os.path.exists(prefs.paths['userPrefsDir']):
        os.mkdir(prefs.paths['userPrefsDir'])
    try:
        if os.path.exists(VERSIONSDIR):
            _checkout(requestedVersion)
        else:
            _clone(requestedVersion)
    except (CalledProcessError, OSError) as e:
        if 'did not match any file(s) known to git' in e.output:
            msg = _translate("'{}' is not a valid PsychoPy version.")
            logging.error(msg.format(requestedVersion))
            raise RuntimeError(msg)
        else:
            raise

    # make sure the checked-out version comes first on the python path:
    sys.path = [VERSIONSDIR] + sys.path
    logging.exp('Prepended `{}` to sys.path'.format(VERSIONSDIR))


def versionOptions(local=True):
    """Available major.minor versions suitable for a drop-down list.

    local=True is fast to search (local only);
        False is slower and variable duration (queries github)

    Returns major.minor versions e.g. 1.83, major e.g., 1., and 'latest'.
    To get patch level versions, use availableVersions().
    """
    majorMinor = sorted(
        list({'.'.join(v.split('.')[:2])
              for v in availableVersions(local=local)}),
        reverse=True)
    major = sorted(list({v.split('.')[0] for v in majorMinor}), reverse=True)
    special = ['latest']
    return special + major + majorMinor


def _localVersions(forceCheck=False):
    global _localVersionsCache
    if forceCheck or not _localVersionsCache:
        if not os.path.isdir(VERSIONSDIR):
            return [psychopy.__version__]
        else:
            cmd = 'git tag'
            tagInfo = subprocess.check_output(cmd.split(), cwd=VERSIONSDIR,
                                              env=constants.ENVIRON).decode('UTF-8')
            allTags = tagInfo.splitlines()
            _localVersionsCache = sorted(allTags, reverse=True)
    return _localVersionsCache


def _remoteVersions(forceCheck=False):
    global _remoteVersionsCache
    if forceCheck or not _remoteVersionsCache:
        try:
            cmd = 'git ls-remote --tags https://github.com/psychopy/versions'
            tagInfo = subprocess.check_output(cmd.split(),
                                              env=constants.ENVIRON,
                                              stderr=subprocess.PIPE)
        except (CalledProcessError, OSError):
            pass
        else:
            if constants.PY3:
                allTags = [line.split('refs/tags/')[1]
                           for line in tagInfo.decode().splitlines()
                           if '^{}' not in line]
            else:
                allTags = [line.split('refs/tags/')[1]
                           for line in tagInfo.splitlines()
                           if '^{}' not in line]
            # ensure most recent (i.e., highest) first
            _remoteVersionsCache = sorted(allTags, reverse=True)
    return _remoteVersionsCache


def _versionFilter(versions, wxVersion):
    """Returns all versions that are compatible with the Python and WX running PsychoPy

    Parameters
    ----------
    versions: list
        All available (valid) selections for the version to be chosen

    Returns
    -------
    list
        All valid selections for the version to be chosen that are compatible with Python version used
    """

    # Get Python 3 Compatibility
    if constants.PY3:
        # msg = _translate("Filtering versions of PsychoPy only compatible with Python 3.")
        # logging.info(msg)
        versions = [ver for ver in versions
                    if ver == 'latest'
                    or parse_version(ver) >= parse_version('1.90')
                    and len(ver) > 1]

    # Get WX Compatibility
    compatibleWX = '4.0'
    if wxVersion is not None and parse_version(wxVersion) >= parse_version(compatibleWX):
        # msg = _translate("wx version: {}. Filtering versions of "
        #                  "PsychoPy only compatible with wx >= version {}".format(wxVersion,
        #                                                                       compatibleWX))
        # logging.info(msg)
        return [ver for ver in versions
                if ver == 'latest'
                or parse_version(ver) > parse_version('1.85.04')
                and len(ver) > 1]
    return versions


def availableVersions(local=True, forceCheck=False):
    """Return all available (valid) selections for the version to be chosen.
    Use local=False to obtain those only available via download
    (i.e., not yet local but could be).

    Everything returned has the form Major.minor.patchLevel, as strings.
    """
    try:
        if local:
            return _localVersions(forceCheck)
        else:
            return sorted(
                list(set([psychopy.__version__] + _localVersions(forceCheck) + _remoteVersions(
                    forceCheck))),
                reverse=True)
    except subprocess.CalledProcessError:
        return []

def fullVersion(partial):
    """Expands a special name or a partial tag to the highest patch level
    in that series, e.g., '1.81' -> '1.81.03'; '1.' -> '1.83.01'
    'latest' -> '1.83.01' (whatever is most recent). Returns '' if no match.

    Idea: 'dev' could mean 'upstream master'.
    """
    # expects availableVersions() return a reverse-sorted list
    if partial in ('', 'latest', None):
        return latestVersion()
    for tag in availableVersions(local=False):
        if tag.startswith(partial):
            return tag
    return ''


def latestVersion():
    """Returns the most recent version available on github
    (or locally if can't access github)
    """
    return availableVersions()[0]


def currentTag():
    """Returns the current tag name from the version repository
    """
    cmd = 'git describe --always --tag'.split()
    tag = subprocess.check_output(cmd, cwd=VERSIONSDIR,
                                  env=constants.ENVIRON).decode('UTF-8').split('-')[0]
    return tag


def _checkout(requestedVersion):
    """Look for a Maj.min.patch requested version, download (fetch) if needed.
    """
    # Check tag of repo
    if currentTag() == requestedVersion:
        return requestedVersion

    # See if the tag already exists in repos
    if requestedVersion not in _localVersions(forceCheck=True):
        # Grab new tags
        msg = _translate("Couldn't find version {} locally. Trying github...")
        logging.info(msg.format(requestedVersion))
        subprocess.check_output('git fetch github --tags'.split(),
                                cwd=VERSIONSDIR,
                                env=constants.ENVIRON).decode('UTF-8')
        # is requested here now? forceCheck to refresh cache
        if requestedVersion not in _localVersions(forceCheck=True):
            msg = _translate("{} is not currently available.")
            logging.error(msg.format(requestedVersion))
            return ''

    # Checkout the requested tag
    cmd = ['git', 'checkout', requestedVersion]
    out = subprocess.check_output(cmd,
                                  stderr=subprocess.STDOUT,
                                  cwd=VERSIONSDIR,
                                  env=constants.ENVIRON).decode('UTF-8')
    logging.debug(out)
    logging.exp('Success:  ' + ' '.join(cmd))
    return requestedVersion


def _clone(requestedVersion):
    """Download (clone) all versions, then checkout the requested version.
    """
    assert not os.path.exists(VERSIONSDIR), 'use `git fetch` not `git clone`'
    print(_translate('Downloading the PsychoPy Library from Github '
                     '(may take a while)'))
    cmd = ('git clone -o github https://github.com/psychopy/versions ' +
           VER_SUBDIR)
    print(cmd)
    subprocess.check_output(cmd.split(), cwd=USERDIR,
                            env=constants.ENVIRON).decode('UTF-8')

    return _checkout(requestedVersion)


def _gitPresent():
    """Check for git on command-line, return bool.
    """
    try:
        gitvers = subprocess.check_output('git --version'.split(),
                                          stderr=subprocess.PIPE,
                                          env=constants.ENVIRON).decode('UTF-8')
    except (CalledProcessError, OSError):
        gitvers = ''
    return bool(gitvers.startswith('git version'))


def _psychopyComponentsImported():
    return [name for name in globals() if name in psychopy.__all__]
