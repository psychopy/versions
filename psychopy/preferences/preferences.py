#!/usr/bin/env python
# -*- coding: utf-8 -*-

import errno
import os
import sys
import platform
from pkg_resources import parse_version
import shutil

try:
    import configobj
    if (sys.version_info.minor >= 7 and
            parse_version(configobj.__version__) < parse_version('5.1.0')):
        raise ImportError('Installed configobj does not support Python 3.7+')
    _haveConfigobj = True
except ImportError:
    _haveConfigobj = False


if _haveConfigobj:  # Use the "global" installation.
    from configobj import ConfigObj
    try:
        from configobj import validate
    except ImportError:  # Older versions of configobj
        import validate
else:  # Use our contrib package if configobj is not installed or too old.
    from psychopy.contrib import configobj
    from psychopy.contrib.configobj import ConfigObj
    from psychopy.contrib.configobj import validate
join = os.path.join


class Preferences:
    """Users can alter preferences from the dialog box in the application,
    by editing their user preferences file (which is what the dialog box does)
    or, within a script, preferences can be controlled like this::

        import psychopy
        psychopy.prefs.hardware['audioLib'] = ['PTB', 'pyo','pygame']
        print(prefs)
        # prints the location of the user prefs file and all the current vals

    Use the instance of `prefs`, as above, rather than the `Preferences` class
    directly if you want to affect the script that's running.
    """

    def __init__(self):
        super(Preferences, self).__init__()
        self.userPrefsCfg = None  # the config object for the preferences
        self.prefsSpec = None  # specifications for the above
        # the config object for the app data (users don't need to see)
        self.appDataCfg = None

        self.general = None
        self.coder = None
        self.builder = None
        self.connections = None
        self.paths = {}  # this will remain a dictionary
        self.keys = {}  # does not remain a dictionary

        self.getPaths()
        self.loadAll()
        # setting locale is now handled in psychopy.localization.init
        # as called upon import by the app

        if self.userPrefsCfg['app']['resetPrefs']:
            self.resetPrefs()

    def __str__(self):
        """pretty printing the current preferences"""
        strOut = "psychopy.prefs <%s>:\n" % (
            join(self.paths['userPrefsDir'], 'userPrefs.cfg'))
        for sectionName in ['general', 'coder', 'builder', 'connections']:
            section = getattr(self, sectionName)
            for key, val in list(section.items()):
                strOut += "  prefs.%s['%s'] = %s\n" % (
                    sectionName, key, repr(val))
        return strOut

    def resetPrefs(self):
        """removes userPrefs.cfg, does not touch appData.cfg
        """
        userCfg = join(self.paths['userPrefsDir'], 'userPrefs.cfg')
        try:
            os.unlink(userCfg)
        except Exception:
            msg = "Could not remove prefs file '%s'; (try doing it manually?)"
            print(msg % userCfg)
        self.loadAll()  # reloads, now getting all from .spec

    def getPaths(self):
        # on mac __file__ might be a local path, so make it the full path
        thisFileAbsPath = os.path.abspath(__file__)
        prefSpecDir = os.path.split(thisFileAbsPath)[0]
        dirPsychoPy = os.path.split(prefSpecDir)[0]
        exePath = sys.executable

        # path to Resources (icons etc)
        dirApp = join(dirPsychoPy, 'app')
        if os.path.isdir(join(dirApp, 'Resources')):
            dirResources = join(dirApp, 'Resources')
        else:
            dirResources = dirApp

        self.paths['psychopy'] = dirPsychoPy
        self.paths['appDir'] = dirApp
        self.paths['appFile'] = join(dirApp, 'PsychoPy.py')
        self.paths['demos'] = join(dirPsychoPy, 'demos')
        self.paths['resources'] = dirResources
        self.paths['tests'] = join(dirPsychoPy, 'tests')
        # path to libs/frameworks
        if 'PsychoPy2.app/Contents' in exePath:
            self.paths['libs'] = exePath.replace("MacOS/python", "Frameworks")
        else:
            self.paths['libs'] = ''  # we don't know where else to look!

        if sys.platform == 'win32':
            self.paths['prefsSpecFile'] = join(prefSpecDir, 'Windows.spec')
            self.paths['userPrefsDir'] = join(os.environ['APPDATA'],
                                              'psychopy3')
        else:
            self.paths['prefsSpecFile'] = join(prefSpecDir,
                                               platform.system() + '.spec')
            self.paths['userPrefsDir'] = join(os.environ['HOME'],
                                              '.psychopy3')

        # Find / copy themes
        self.paths['themes'] = join(self.paths['userPrefsDir'], 'themes')
        baseThemes = join(self.paths['appDir'], 'themes')
        baseAppThemes = join(self.paths['appDir'], 'themes', 'app')
        # Find / copy fonts
        self.paths['fonts'] = join(self.paths['userPrefsDir'], 'fonts')
        # avoid silent fail-to-launch-app if bad permissions:

        try:
            os.makedirs(self.paths['userPrefsDir'])
        except OSError as err:
            if err.errno != errno.EEXIST:
                raise
        # Create themes folder in user space if not one already
        try:
            os.makedirs(self.paths['themes'])
        except OSError as err:
            if err.errno != errno.EEXIST:
                raise
        try:
            os.makedirs(join(self.paths['themes'], "app"))
        except OSError as err:
            if err.errno != errno.EEXIST:
                raise
        # Make fonts folder in user space if not one already
        try:
            os.makedirs(self.paths['fonts'])
        except OSError as err:
            if err.errno != errno.EEXIST:
                raise
        # Make sure all the base themes are present in user's folder
        #try:
        for file in os.listdir(baseThemes):
            if file.endswith('.json'):
                shutil.copyfile(
                    join(baseThemes, file),
                    join(self.paths['themes'], file)
                )
        for file in os.listdir(baseAppThemes):
            if file.endswith('.json'):
                shutil.copyfile(
                    join(baseAppThemes, file),
                    join(self.paths['themes'], "app", file)
                    )

    def loadAll(self):
        """Load the user prefs and the application data
        """
        self._validator = validate.Validator()

        # note: self.paths['userPrefsDir'] gets set in loadSitePrefs()
        self.paths['appDataFile'] = join(
            self.paths['userPrefsDir'], 'appData.cfg')
        self.paths['userPrefsFile'] = join(
            self.paths['userPrefsDir'], 'userPrefs.cfg')

        # If PsychoPy is tucked away by Py2exe in library.zip, the preferences
        # file cannot be found. This hack is an attempt to fix this.
        libzip = "\\library.zip\\psychopy\\preferences\\"
        if libzip in self.paths["prefsSpecFile"]:
            self.paths["prefsSpecFile"] = self.paths["prefsSpecFile"].replace(
                libzip, "\\resources\\")

        self.userPrefsCfg = self.loadUserPrefs()
        self.appDataCfg = self.loadAppData()
        self.validate()

        # simplify namespace
        self.general = self.userPrefsCfg['general']
        self.app = self.userPrefsCfg['app']
        self.coder = self.userPrefsCfg['coder']
        self.builder = self.userPrefsCfg['builder']
        self.hardware = self.userPrefsCfg['hardware']
        self.connections = self.userPrefsCfg['connections']
        self.appData = self.appDataCfg

        # keybindings:
        self.keys = self.userPrefsCfg['keyBindings']

    def loadUserPrefs(self):
        """load user prefs, if any; don't save to a file because doing so
        will break easy_install. Saving to files within the psychopy/ is
        fine, eg for key-bindings, but outside it (where user prefs will
        live) is not allowed by easy_install (security risk)
        """
        self.prefsSpec = ConfigObj(self.paths['prefsSpecFile'],
                                   encoding='UTF8', list_values=False)

        # check/create path for user prefs
        if not os.path.isdir(self.paths['userPrefsDir']):
            try:
                os.makedirs(self.paths['userPrefsDir'])
            except Exception:
                msg = ("Preferences.py failed to create folder %s. Settings"
                       " will be read-only")
                print(msg % self.paths['userPrefsDir'])
        # then get the configuration file
        cfg = ConfigObj(self.paths['userPrefsFile'],
                        encoding='UTF8', configspec=self.prefsSpec)
        # cfg.validate(self._validator, copy=False)  # merge then validate
        # don't cfg.write(), see explanation above
        return cfg

    def saveUserPrefs(self):
        """Validate and save the various setting to the appropriate files
        (or discard, in some cases)
        """
        self.validate()
        if not os.path.isdir(self.paths['userPrefsDir']):
            os.makedirs(self.paths['userPrefsDir'])
        self.userPrefsCfg.write()

    def loadAppData(self):
        # fetch appData too against a config spec
        appDataSpec = ConfigObj(join(self.paths['appDir'], 'appData.spec'),
                                encoding='UTF8', list_values=False)
        cfg = ConfigObj(self.paths['appDataFile'],
                        encoding='UTF8', configspec=appDataSpec)
        resultOfValidate = cfg.validate(self._validator,
                                        copy=True,
                                        preserve_errors=True)
        self.restoreBadPrefs(cfg, resultOfValidate)
        # force favComponent level values to be integers
        if 'favComponents' in cfg['builder']:
            for key in cfg['builder']['favComponents']:
                _compKey = cfg['builder']['favComponents'][key]
                cfg['builder']['favComponents'][key] = int(_compKey)
        return cfg

    def saveAppData(self):
        """Save the various setting to the appropriate files
        (or discard, in some cases)
        """
        # copy means all settings get saved:
        self.appDataCfg.validate(self._validator, copy=True)
        if not os.path.isdir(self.paths['userPrefsDir']):
            os.makedirs(self.paths['userPrefsDir'])
        self.appDataCfg.write()

    def validate(self):
        """Validate (user) preferences and reset invalid settings to defaults
        """
        result = self.userPrefsCfg.validate(self._validator, copy=True)
        self.restoreBadPrefs(self.userPrefsCfg, result)

    def restoreBadPrefs(self, cfg, result):
        """result = result of validate
        """
        if result == True:
            return
        vtor = validate.Validator()
        for sectionList, key, _ in configobj.flatten_errors(cfg, result):
            if key is not None:
                _secList = ', '.join(sectionList)
                val = cfg.configspec[_secList][key]
                cfg[_secList][key] = vtor.get_default_value(val)
            else:
                msg = "Section [%s] was missing in file '%s'"
                print(msg % (', '.join(sectionList), cfg.filename))

prefs = Preferences()
