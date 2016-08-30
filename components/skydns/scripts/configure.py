#!/usr/bin/env python

import tempfile
from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA


SKYDNS_SERVICE_NAME = 'skydns'

with tempfile.NamedTemporaryFile(delete=False, mode='wb') as f:
    f.write('nameserver 127.0.0.1\n')
    with open('/etc/resolv.conf') as source:
        f.write(source.read())

utils.sudo('mv {0} /etc/resolv.conf'.format(f.name))
utils.systemd.configure(SKYDNS_SERVICE_NAME)
utils.systemd.systemctl('daemon-reload')
