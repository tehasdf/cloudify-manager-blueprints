HA Cloudify Manager
===================

The `ha-manager-blueprint.yaml` blueprint spawns a replicated manager, ie. two
instances of the manager. A virtual ip is used to route to the "master", and
when that dies, it is routed to the "replica" (one of the replicas) instead.

It's also possible to transition to an active/active load balanced setup in
the future (see the notes about each component for details).


Blueprint structure
-------------------

Replication is done using scaling groups in the blueprint. There are nodes that
hold cluster-wide configuration (the "cluster_configuration" node), that aren't
replicated.

The cluster_configuration has a cluster_config property which is a list of dicts
holding the config (fabric env, etc) for each individual machine. See the example
input file (`ha_inputs.yaml`) for the structure of the cluster config.

`manager_host_configuration` is a replicated (ie. it belongs to the scaling
group) node that holds the config for one machine. It has a relationship to
the cluster config, and simply does a .pop() from the list of cluster_config dicts
to choose one of them.
The machine config is set as a runtime property on the `manager_host_configuration`
instance.

All tasks that use fabric will reference that runtime property in the inputs, eg.

.. code-block:: yaml

        start:
          implementation: fabric.fabric_plugin.tasks.run_script
          inputs:
            script_path: (...)
            fabric_env:
              default: { get_attribute: [manager_host_configuration, fabric_env] }

Cloudify will make sure that it uses the right `manager_host_configuration`
instance from the group.


Moving forward, I think using scaling groups wasn't the best idea, and instead
we could simply have one blueprint that we'd install on each machine by hand
(which would be more flexible, and paralellizable, even if less "pure").


Additional consul cluster
-------------------------

Note that consul requires at least 3 machines for any fault tolerance (it can't
use just 2, because quorum of 2 is 2 :) So if one machine was to die, the cluster
would've been left unusable).

For now, we're just using 2 machines for the manager (master+replica), so there's
an additional "consul cluster" scaling group in the blueprint, that contains
machines that only run consul.

If you're trying to run a cloudify manager cluster containing 2 machines, make
sure to have 1 machine in the additional consul cluster. If the manager cluster
has 3 machines, you don't need the additional one.

The consul cluster is configured the same way as the manager cluster, using
a list of config dicts, input: `consul_cluster_config`


Components
==========

Manager config
--------------

The floating ip is set as the 'public ip' for the `set_manager_ips.py` script
to use. This allows mgmtworker and the agents to use that ip to communicate with
the manager.


Keepalived
----------

The virtual ip is managed by keepalived. Current implementation supports a local
virtualbox network, but it should work on eg. openstack with minimal changes.

With virtualbox, you need to choose an IP yourself, and pass it as the `floating_ip`
input.
Keepalived will be configured with one `vrrp_instance`, only to manage the floating
ip. See the `components/keepalive/config/keepalive.conf.tmpl` file for the
config template.

In the future, we could also add load balancing services using keepalived
(`virtual_server`) when building a active/active load balanced architecture.


Consul
------

Consul is used as the k/v store to support postgresql and fileserver clustering.
When implementing a load-balanced solution, we'll want to create "services" in
consul (for the REST service, possibly also rabbitmq) with health checks, and
load balance using those (see comments on nginx).


Rabbitmq
--------

Currently, each instance of rabbitmq is separate from others. This is easy to
set up, but for has no redundancy, ie. if rabbitmq (or the whole machine) goes
down, clients won't be able to continue the workflow (resumable workflows aren't
currently possible also for other reasons, though).

Clients (management worker and agents) use the virtual ip to connect to rabbitmq.


Postgresql
----------

We use stolon (https://github.com/sorintlab/stolon) as the postgres clustering
solution. Each node runs 3 components:

- the stolon sentinel - a daemon that uses consul to communicate with other
  instances of the sentinel, and checks if it needs to transition from
  replica to master
- stolon keeper: a wrapper that actually runs postgresql and listens
  for commands from the sentinel. Postgresql's builtin replication is used
  to copy data from master to the replicas (set up by stolon)
- stolon proxy - each machine runs a proxy service that connects to the
  current postgresql (ie. keeper) master. This means clients on every machine
  (ie. rest service) can just connect to the proxy on localhost, and the proxy
  will make sure they talk to the master

Moving forward: the main problem with stolon is connection resets on master
transition. We might consider using pgpool2 instead of the stolon proxy.
Alternatively, setting up replication ourselves would give us more control,
but so far it seems the sentinel+keeper layer in stolon is pretty good.


Nginx & REST service
-----

Currently, every nginx instance only reverse-proxies to the local REST service
(and fileserver). This is the same behaviour as the regular manager.
Clients (cli, agents, mgmtworker) use the virtual ip to connect, so they always
connect to the current master machine.

Instead, we could have each nginx load-balance between all live REST services
in the cluster (using consul for the health checks). In that case, we'd use
consul-template to update nginx's config file and restart it when needed.


Fileserver
----------

Fileserver replication is done using syncthing (https://syncthing.net/), by
setting it to replicate `/opt/manager/resources`. Syncthing watches the directory
for changes (added or deleted files) and propagates that to all the machines in
the cluster.

This is a multi-master solution in the sense that if we upload something to
the replica machine, that will also be replicated to the master machine.
(of course, clients use the virtual ip to connect, so realistically they will
only ever upload to the master).

Consul is used to store the addresses (and syncthing connection defaults) of
the machines in the cluster, and confd to template syncthing configuration
files from that.

Unfortunately this is asynchronous replication, so if the user uploads something
and the manager dies right after that, the client will still see success even if
the files weren't replicated yet.

In the future, we might add something to mitigate that risk, eg. after every
request, the REST service might poll syncthing's API to ask if the files are
synced.
(also, we should use consul-template instead of confd)


Mgmtworker
----------

Unchanged, other than using the virtual ip for rabbitmq, the REST service, and
the fileserver.



Out of scope components
=======================

Elasticsearch
-------------

Not replicated at all.


Influxdb, riemann, logstash
-----------------

Removed from the blueprint
