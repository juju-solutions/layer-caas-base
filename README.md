# Overview
<a href="https://opensource.org/licenses/Apache-2.0"><img src="https://img.shields.io/badge/License-Apache%202.0-blue.svg" alt="Apache 2.0 License"></a>

This is the base layer for all CAAS reactive Charms. It provides all of the standard
Juju hooks and starts the reactive framework when these hooks get executed.

# Usage

Any CAAS or Kubernetes charm should include this in its `layer.yaml`.  It is
also recommended to include `layer:docker-resource`:

```yaml
includes:
  - 'layer:caas-base'
  - 'layer:docker-resource'
```

The charm can then define its Docker image as a resource in `metadata.yaml`:

```yaml
name: my-charm
resources:
  my-image:
    description: 'Docker image for this charm'
    type: docker
```

When ready, the charm should call `pod_spec_set` with the relevant data structure:

```python
from charmhelpers.core import hookenv
from charms.reactive import set_flag, when, when_not

from charms import layer


@when_not('layer.docker-resource.my-image.fetched')
def fetch_image():
    layer.docker_resource.fetch('my-image')


@when('layer.docker-resource.my-image.available')
@when_not('charm.my-charm.started')
def create_container():
    layer.status.maintenance('configuring container')

    image_info = layer.docker_resource.get_info('my-image')
    config = hookenv.config()

    success = layer.caas_base.pod_spec_set({
        'containers': [
            {
                'name': 'my-charm',
                'imageDetails': {
                    'imagePath': image_info.registry_path,
                    'username': image_info.username,
                    'password': image_info.password,
                },
                'ports': [
                    {
                        'name': 'service',
                        'containerPort': 80,
                    },
                ],
                'config': {
                    'SOME_VALUE': config['some-option'],
                },
                'files': [
                    {
                        'name': 'configs',
                        'mountPath': '/etc/config',
                        'files': {
                            'my-charm.conf': Path('files/my-charm.conf').read_text(),
                        },
                    },
                ],
            },
        ],
    })
    if success:
        layer.status.maintenance('creating container')
        set_flag('charm.my-charm.started')
    else:
        layer.status.blocked('k8s spec failed to deploy')
```
