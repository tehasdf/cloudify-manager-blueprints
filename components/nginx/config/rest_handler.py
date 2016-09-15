#!/opt/manager/env/bin/python

import json
import subprocess
import urllib2
from jinja2 import Template

resp = urllib2.urlopen(
    'http://{{ ctx.source.instance.host_ip}}:8500/v1/health/service/rest?passing')

data = json.load(resp)
servers = []
for service in data:
    servers.append({
        'ip': service['Service']['Address'],
        'port': service['Service']['Port']
    })

with open('/opt/cloudify/consul/nginx.tmpl') as f:
    t = Template(
        f.read(),
        block_start_string='<%',
        block_end_string='%>',
        variable_start_string='<<',
        variable_end_string='>>',
        comment_start_string='<#',
        comment_end_string='#>',
    )

template_context = {
    'rest_services': servers,
    'fileservers': servers
}

with open('/etc/nginx/conf.d/default.conf', 'w') as f:
    f.write(t.render(**template_context))

subprocess.check_call(['systemctl', 'kill', '-s', 'HUP', 'nginx'])
