#!/usr/bin/env python

from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA


for service_name in ['stolon-sentinel', 'stolon-keeper', 'stolon-proxy']:
    utils.systemd.configure(service_name)
    utils.start_service(service_name)
    utils.systemd.verify_alive(service_name)
