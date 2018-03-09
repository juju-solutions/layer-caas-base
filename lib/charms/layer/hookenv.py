import errno
import os
import subprocess
import tempfile

from charmhelpers.core.hookenv import log


def pod_spec_set(spec):
    log('set pod spec:\n{}'.format(spec), level='TRACE')
    with tempfile.NamedTemporaryFile(delete=False) as spec_file:
        spec_file.write(spec.encode("utf-8"))
    cmd = ['pod-spec-set', "--file", spec_file.name]

    try:
        ret = subprocess.call(cmd)
        os.remove(spec_file.name)
        if ret == 0:
            return
    except OSError as e:
        if e.errno != errno.ENOENT:
            raise
    log_message = 'pod-spec-set failed'
    log(log_message, level='INFO')
