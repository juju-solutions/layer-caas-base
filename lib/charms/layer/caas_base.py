import os
from importlib import import_module
from pathlib import Path
from subprocess import run, PIPE, CalledProcessError
import re

import yaml
from charmhelpers.core.hookenv import log


def pod_spec_set(spec, k8s_resources=None):
    if not isinstance(spec, str):
        spec = yaml.dump(spec)

    if k8s_resources is not None:
        if not isinstance(k8s_resources, str):
            k8s_resources = yaml.dump(k8s_resources)

        spec += k8s_resources

    try:
        run(['pod-spec-set'], stdout=PIPE, stderr=PIPE, check=True, input=spec.encode('utf-8'))
    except CalledProcessError as err:
        stderr = err.stderr.decode('utf-8').strip()
        log(f'pod-spec-set encountered an error: `{stderr}`', level='ERROR')

        if re.match(r'^ERROR application [\w-]+ not alive$', stderr):
            log('Ignored error due to pod-spec-set getting called during app removal', level='INFO')
            return

        raise


def init_config_states():
    import yaml
    from charmhelpers.core import hookenv
    from charms.reactive import set_state
    from charms.reactive import toggle_state

    config = hookenv.config()

    config_defaults = {}
    config_defs = {}
    config_yaml = os.path.join(hookenv.charm_dir(), 'config.yaml')
    if os.path.exists(config_yaml):
        with open(config_yaml) as fp:
            config_defs = yaml.safe_load(fp).get('options', {})
            config_defaults = {key: value.get('default')
                               for key, value in config_defs.items()}
    for opt in config_defs.keys():
        if config.changed(opt):
            set_state('config.changed')
            set_state('config.changed.{}'.format(opt))
        toggle_state('config.set.{}'.format(opt), config.get(opt))
        toggle_state('config.default.{}'.format(opt),
                     config.get(opt) == config_defaults[opt])
    hookenv.atexit(clear_config_states)


def clear_config_states():
    from charmhelpers.core import hookenv, unitdata
    from charms.reactive import remove_state

    config = hookenv.config()

    remove_state('config.changed')
    for opt in config.keys():
        remove_state('config.changed.{}'.format(opt))
        remove_state('config.set.{}'.format(opt))
        remove_state('config.default.{}'.format(opt))
    unitdata.kv().flush()


def import_layer_libs():
    """
    Ensure that all layer libraries are imported.

    This makes it possible to do the following:

        from charms import layer

        layer.foo.do_foo_thing()

    Note: This function must be called after bootstrap.
    """
    for module_file in Path('lib/charms/layer').glob('*'):
        module_name = module_file.stem
        if module_name in ('__init__', 'caas_base', 'execd') or not (
            module_file.suffix == '.py' or module_file.is_dir()
        ):
            continue
        import_module('charms.layer.{}'.format(module_name))
