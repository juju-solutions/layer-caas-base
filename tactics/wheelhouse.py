import logging

from charmtools.build.tactics import ExactMatch, Tactic
from charmtools import utils

log = logging.getLogger(__name__)


class WheelhouseTactic(ExactMatch, Tactic):
    kind = "dynamic"
    FILENAME = 'wheelhouse.txt'

    def __init__(self, *args, **kwargs):
        super(WheelhouseTactic, self).__init__(*args, **kwargs)
        self.tracked = []
        self.previous = []

    @property
    def dest(self):
        return self.target.directory / 'lib'

    def __str__(self):
        return "Building wheelhouse in {}".format(self.dest)

    def combine(self, existing):
        self.previous = existing.previous + [existing]
        return self

    def __call__(self):
        # recursively process previous layers, depth-first
        for tactic in self.previous:
            tactic()
        # process this layer
        self.dest.mkdir_p()
        with utils.tempdir(chdir=False) as temp_dir:
            # put in a temp dir first to track new and updated files
            utils.Process(
                ('pip3', 'install', '-t', str(temp_dir), '-r', self.entity)
            ).exit_on_error()()
            # clear out cached compiled files
            for path in temp_dir.walk():
                if path.isdir() and (
                    path.basename() == '__pycache__' or
                    path.basename().endswith('.dist-info')
                ):
                    path.rmtree()
                elif path.isfile() and path.basename().endswith('.pyc'):
                    path.remove()
            # add to set of files to sign
            self.tracked.extend([self.dest / file.relpath(temp_dir)
                                 for file in temp_dir.walkfiles()])
            # copy everything over from temp_dir to self.dest
            temp_dir.merge_tree(self.dest)

    def sign(self):
        """return sign in the form {relpath: (origin layer, SHA256)}

        This is how the report of changed files is created.
        """
        sigs = {}
        # recursively have all previous layers sign their files, depth-first
        for tactic in self.previous:
            sigs.update(tactic.sign())
        # sign ownership of all files this layer created or updated
        for d in self.tracked:
            relpath = d.relpath(self.target.directory)
            sigs[relpath] = (self.layer.url, "dynamic", utils.sign(d))
        return sigs
