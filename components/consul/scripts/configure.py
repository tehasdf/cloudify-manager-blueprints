#!/usr/bin/env python

from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA


CONSUL_SERVICE_NAME = 'consul'
ctx_properties = utils.ctx_factory.get(CONSUL_SERVICE_NAME)

utils.systemd.configure(CONSUL_SERVICE_NAME)
utils.systemd.systemctl('daemon-reload')
