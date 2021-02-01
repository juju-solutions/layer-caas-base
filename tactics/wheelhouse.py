import logging

from charmtools.build.tactics import WheelhouseTactic
from charmtools import utils

log = logging.getLogger(__name__)


class CAASWheelhouseTactic(WheelhouseTactic):
    @property
    def dest(self):
        return self.target.directory / 'lib'

    def _add(self, wheelhouse, *reqs):
        with utils.tempdir(chdir=False) as temp_dir:
            # install into a temp dir first to track new and updated files
            utils.Process(
                ('pip3', 'install', '-t', str(temp_dir), *reqs)
            ).exit_on_error()()
            # clear out cached compiled files (there shouldn't really be a
            # reason to include these in the charms; they'll just be
            # recompiled on first run)
            for path in temp_dir.walk():
                if path.isdir() and (
                    path.basename() == '__pycache__' or
                    path.basename().endswith('.dist-info')
                ):
                    path.rmtree()
                elif path.isfile() and path.basename().endswith('.pyc'):
                    path.remove()
            # track all the files that were created by this layer
            self.tracked.extend([self.dest / file.relpath(temp_dir)
                                 for file in temp_dir.walkfiles()])
            # copy everything over from temp_dir to charm's /lib
            temp_dir.merge_tree(self.dest)
