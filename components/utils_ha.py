
import os
import json
import stat
import urllib2
import tempfile

from cloudify import ctx
from contextlib import contextmanager
from xml.etree import ElementTree
from collections import MutableMapping, MutableSequence

import utils


POSTGRES_BIN_DIR = '/usr/pgsql-9.5/bin/'
REPMGR_CONFIG = '/etc/repmgr.conf'


class ConsulKV(MutableMapping):
    """An interface to the consul key/value store. Use this like a dict.

    For traversing subdirectories, use the subdir method.
    Note that this does no caching, so accessing nested directories
    might run lots of requests.
    """

    def __init__(self, path='', base_url='http://127.0.0.1:8500'):
        self._base_url = base_url
        self._path = path

    def subdir(self, path):
        return self.__class__(path='{0}{1}/'.format(self._path, path),
                              base_url=self._base_url)

    @property
    def _url(self):
        return '{0}/v1/kv/{1}'.format(self._base_url, self._path)

    def _parse_response(self, response):
        content = json.load(response)
        return {
            element['Key']: json.loads(element['Value'].decode('base64'))
            for element in content
        }

    def _get(self, key):
        url = '{0}/{1}'.format(self._url, key)
        get_response = urllib2.urlopen(url)
        return self._parse_response(get_response)

    def _list(self):
        url = '{0}?keys'.format(self._url)
        list_response = urllib2.urlopen(url)
        keys = json.load(list_response)
        return {
            key.replace(self._path, '').lstrip('/').split('/')[0]
            for key in keys
        }

    def __getitem__(self, key):
        key = key.rstrip('/')
        try:
            value = self._get(key)
        except urllib2.HTTPError as e:
            if e.code != 404:
                raise
            raise KeyError(key)
        else:
            return value[self._path + key]

    def __setitem__(self, key, value):
        ctx.logger.debug('Consul: setting {0} to {1}'.format(key, value))

        url = '{0}{1}'.format(self._url, key)
        put_request = urllib2.Request(url, data=json.dumps(value))
        put_request.get_method = lambda: 'PUT'
        put_response = urllib2.urlopen(put_request)
        put_successful = json.load(put_response)
        if not put_successful:
            raise ctx.abort_operation(
                'PUT request failed: {0}'.format(put_successful))

    def __delitem__(self, key):
        ctx.logger.debug('Consul: deleting {0}'.format(key))

        url = '{0}{1}'.format(self._url, key)
        delete_request = urllib2.Request(url,)
        delete_request.get_method = lambda: 'DELETE'
        urllib2.urlopen(delete_request)

    def __iter__(self):
        return iter(self._list())

    def __len__(self):
        return len(self.keys())

    def __repr__(self):
        return '<{0} {1}: {2}>'.format(self.__class__.__name__, self._base_url,
                                       self._path)


class ConsulWatches(MutableSequence):
    """An interface to the list of all defined consul watches."""
    CONSUL_SERVICE_NAME = 'consul'

    def __init__(self, config_directory='/etc/consul.d',
                 save_filename='watches.json'):
        self._config_directory = config_directory
        self._loaded = False
        self._watches = None
        self._save_filename = save_filename

    @property
    def watches(self):
        if not self._loaded:
            self._watches = self._load()
        return self._watches

    def _load(self):
        all_watches = []
        for filename in os.listdir(self._config_directory):
            filepath = os.path.join(self._config_directory, filename)
            with open(filepath) as f:
                consul_config = json.load(f)
            all_watches.extend(consul_config.get('watches', []))
        return all_watches

    def _save(self):
        ctx.logger.debug('Consul: saving {0} watches'.format(len(self)))

        filepath = os.path.join(self._config_directory, self._save_filename)
        with open(filepath, 'w') as f:
            json.dump({'watches': self.watches}, f)
        utils.systemd.reload(self.CONSUL_SERVICE_NAME)

    def __getitem__(self, index):
        return self.watches[index]

    def __setitem__(self, index, value):
        self.watches[index] = value
        self._save()

    def __delitem__(self, index):
        del self.watches[index]
        self._save()

    def insert(self, index, value):
        self.watches.insert(index, value)
        self._save()

    def __iter__(self):
        return iter(self.watches)

    def __len__(self):
        return len(self.watches)


@contextmanager
def sudo_open(path, mode):
    ctx.logger.info('sudo-opening {0} ({1})'.format(path, mode))
    fd, tmp_path = tempfile.mkstemp()
    os.close(fd)

    stat_result = utils.sudo(['stat', path], ignore_failures=True)
    if stat_result.returncode != 0:
        # file doesn't exist - only continue if we're using a mode that
        # would create it
        if not set(mode) & set('wa'):
            ctx.abort_operation('{0} does not exist'.format(path))
    else:
        utils.copy(path, tmp_path)

    try:
        original_chmod = get_chmod(tmp_path)
        utils.chmod('a+rw', tmp_path)
        with open(tmp_path, mode) as f:
            yield f
        utils.chmod(original_chmod, tmp_path)
        # if the file was opened for writing, overwrite the original
        if 'w' in mode or 'a' in mode or 'r+' in mode:
            utils.move(tmp_path, path)
    finally:
        utils.remove(tmp_path)


def get_chmod(path):
    """Chmod of path in a format that can be used with /bin/chmod."""
    stat_mode = os.stat(path).st_mode
    return oct(stat.S_IMODE(stat_mode))


def _get_local_network_cidr():
    return ctx.instance.host_ip.rsplit('.', 1)[0] + '.0/24'


def run_postgres_command(command, **kwargs):
    if not os.path.isabs(command[0]):
        command[0] = os.path.join(POSTGRES_BIN_DIR, command[0])
    return utils.sudo(command, user='postgres', **kwargs)


def run_repmgr_command(command, **kwargs):
    run_postgres_command(['repmgr', '-f', REPMGR_CONFIG] + command, **kwargs)


def psql(cmd):
    return run_postgres_command(['psql', '-c', cmd], ignore_failures=True)


class SyncthingAPI(object):
    """Interface to the syncthing API."""
    def __init__(self,
                 base_url='http://127.0.0.1:8384/rest',
                 config_path='/root/.config/syncthing/config.xml'):
        self._base_url = base_url
        self._config_path = config_path
        self._api_key = None

    def api_key(self):
        if self._api_key is None:
            with sudo_open(self._config_path) as f:
                config_source = f.read()
            tree = ElementTree.fromstring(config_source)
            self._api_key = tree.findall('.//gui/apikey')[0].text
        return self._api_key

    def status(self):
        return self._json_request('system/status')

    def get_id(self):
        return self.status()['myID']

    def _json_request(self, path, data=None, method='GET'):
        url = '{0}/{1}'.format(self._base_url, path)
        headers = {'X-Api-Key': self.api_key}
        req = urllib2.Request(url, data=data, headers=headers)
        req.get_method = lambda: method
        resp = urllib2.urlopen(req)
        return json.load(resp)


local_network_cidr = _get_local_network_cidr()
consul_kv = ConsulKV()
consul_watches = ConsulWatches()
syncthing_api = SyncthingAPI()
