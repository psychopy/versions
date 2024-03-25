import json
import os
import numpy as np
from pathlib import Path
from psychopy.preferences import prefs


class Shelf:
    """

    Parameters
    ----------
    scope : str
        Scope of the Shelf file, one of:
        - "designer" / "d" / "des" / "user": Shelf file is accessible to any experiment running on this computer. File
          will be stored in your user folder (%AppData%/psychopy3 on Windows) as `shelf.json`.
        - "experiment" / "e" / "exp" / "project": Shelf file is accessible only to the given experiment. File will be
          stored in the experiment folder as `shelf.json`.
        - "participant" / "p" / "par" / "subject": Shelf file is accessible only to the given participant. File will be
          stored in the "shelf" folder within your user folder as the participant ID followed by `.json`
    expPath : str or Path
        Path to the experiment folder, if scope is "experiment". Can also accept a path to the experiment file.
    participant : str
        Participant ID, if scope is "participant".
    """

    # other names which scopes can be referred to as
    scopeAliases = {
        'designer': ["designer", "d", "des", "user"],
        'experiment': ["experiment", "e", "exp", "project"],
        'participant': ["participant", "p", "par", "subject"]
    }

    def __init__(self, scope="experiment", expPath=None, participant=None):
        # handle scope aliases
        scope = self.scopeFromAlias(scope)

        # if given an experiment path, sanitize it
        if expPath is not None:
            # convert to Path object
            expPath = Path(expPath)
            # if given a file path, use parent dir
            if not expPath.is_dir():
                expPath = expPath.parent

        # work out path of scope file from scope and params
        if scope == "designer":
            # access shelf from user folder
            self.path = Path(prefs.paths['userPrefsDir']) / "shelf.json"
        elif scope in "experiment":
            # make sure we have the information we need to get scope file
            assert expPath is not None, (
                "Cannot access experiment-scope shelf records without reference to experiment's origin path. Please "
                "supply a value for 'expPath' when creating an experiment-scope Shelf object."
            )
            # access shelf from experiment folder
            self.path = expPath / "shelf.json"
        elif scope in "participant":
            # make sure we have the information we need to get scope file
            assert participant is not None, (
                "Cannot access participant-scope shelf records without reference to participant ID. Please "
                "supply a value for 'participant' when creating a participant-scope Shelf object."
            )
            # access shelf from a participant shelf file in the user folder
            self.path = Path(prefs.paths['userPrefsDir']) / "shelf" / f"{participant}.json"

        # open file(s)
        self.data = ShelfData(self.path)

    @staticmethod
    def scopeFromAlias(alias):
        """
        Get the scope name from one of its aliases, e.g. get "experiment" from "exp".

        Parameters
        ----------
        alias : str
            Alias of the scope.

        Returns
        -------
        str
            Proper name of the scope.
        """
        # if alias is present in aliases dict, return corresponding scope
        for scope in Shelf.scopeAliases:
            if alias in Shelf.scopeAliases[scope]:
                return scope
        # if it isn't aliased, return as is
        return alias

    def counterBalanceSelect(self, key, groups, groupSizes):
        """
        Select a group from a counterbalancing entry and decrement the associated counter.

        Parameters
        ----------
        key : str
            Key of the entry to draw from
        groups : list[str]
            List of group names. Names not present in the entry will be created with the matching groupSize value.
        groupSizes : list[int]
            List of group max sizes, must be the same length as `groups`. The probability of each group being chosen is
            determined by its number of remaining participants.

        Returns
        -------
        str
            Chosen group name
        bool
            True if the given group is now at 0, False otherwise
        """
        # get entry
        try:
            entry = self.data[key]
        except KeyError:
            entry = {}

        # for each group...
        options = []
        weights = []
        for group, size in zip(groups, groupSizes):
            group = str(group)
            # make sure it exists in entry
            if group not in entry:
                entry[group] = size
            # figure out weight from cap
            weight = size / sum(groupSizes)
            # add to options if not full
            if entry[group] > 0:
                options.append(group)
                weights.append(weight)

        # make sure weights sum to 1
        weights = weights / np.sum(weights)
        # choose a group at random
        try:
            chosen = np.random.choice(options, p=weights)
        except ValueError:
            # if no groups, force to be None
            return None, True
        # iterate chosen group
        entry[chosen] -= 1
        # get finished
        finished = entry[chosen] <= 0

        # set entry
        self.data[key] = entry

        return chosen, finished


class ShelfData:
    """
    Dict-like object representing the data on a Shelf. ShelfData is linked to a particular JSON file - when its data
    changes, the file is written to, keeping it in sync.


    Parameters
    ----------
    path : str or Path
        Path to the JSON file which this ShelfData corresponds to.
    """
    def __init__(self, path):
        # make sure path exists
        if not path.parent.is_dir():
            os.makedirs(str(path.parent), exist_ok=True)
        if not path.is_file():
            path.write_text("{}", encoding="utf-8")
        # store ref to path
        self._path = path
        # make sure file is valid json
        try:
            self.read()
        except json.JSONDecodeError as err:
            errcls = type(err)
            raise json.JSONDecodeError((
                    f"Contents of shelf file '{path}' are not valid JSON syntax. Has the file been edited outside of "
                    f"PsychoPy? Original error:\n"
                    f"\t{errcls.__module__}.{errcls.__name__}: {err.msg}"
                ),
                doc=err.doc,
                pos=err.pos
            )

    def __repr__(self):
        # get data from file
        data = self.read()

        return repr(data)

    def __contains__(self, item):
        data = self.read()

        return item in data

    def read(self):
        """
        Get data from linked JSON file.

        Returns
        -------
        dict
            Data read from file.
        """
        # get data from file
        with self._path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        return data

    def __getitem__(self, key):
        # get data from file
        data = self.read()

        return data[key]

    def write(self, data):
        """
        Write data to linked JSON file

        Parameters
        ----------
        data : dict
            Data to write to file.
        """
        # write data to file
        with self._path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=True)

    def __setitem__(self, key, value):
        # get data from file
        data = self.read()
        # set data
        data[key] = value
        # write data to file
        self.write(data)
