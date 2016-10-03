Cloudify HA Manager
~~~~~~~~~~~~~~~~~~~

The main ideas behind the HA design are:

    - a cluster is created (usually 3 or 5 machines) by bootstrapping a master
      manager, and then bootstrapping several replica managers, passing to each
      the IP of any of the machines in the cluster
    - all configuration is done using consul. Ideally, address of a consul
      instance belonging to the cluster is all that is needed to join the cluster
    - outside communication is managed using keepalived and a LVS virtual IP.
      This means the cluster advertises a virtual IP that points to the current
      "active" manager; agents and the CLI must use the virtual IP to communicate
      with the manager. If the active manager goes down, the virtual IP will be
      taken over by a replica.
    - note that replicas work in "hot standby" mode - they can be used at any
      time, and will proxy write requests to the current master. This will never
      happen with the current implementation, as only the master is accessible
      from outside (via the virtual ip), but would allow load-balancing requests
      in the future
    - postgresql and the fileserver are services that keep state that must be
      replicated across all nodes in the cluster. Rabbitmq and elasticsearch
      are NOT replicated
    - currently it's not strictly enforced that the machine holding the virtual
      IP is also the database master server (keepalived and repmgr use the
      same mechanism to determine priority, so this should actually always be
      the case, but nothing is done to ensure it). In the future we can add
      scripts that enforce this constraint, or actually do the opposite: allow
      configuring the cluster so that eg. a machine with the fastest CPU
      holds the virtual IP (ie. will handle HTTP requests and run operations),
      while the machine with the fastest disk is the database master.


Components
==========

Consul
------

During configuration, the 'consul_join' parameter is examine: if it is empty,
then a new consul cluster is initialized. Otherwise, it must be an array of
addresses of existing machines in the cluster. It is not necessary to provide
the addresses of all the machines - just one is enough.


Keepalived
----------

A simple `vrrp_instance` entry is used to manage the virtual IP.
The 'virtualip' parameter needs to be provided when bootstrapping the master
server, it is not required for machines that are joining the cluster.

Consul's key/value store is used to manage the configuration of keepalived
instances. During configuration, the "keepalived/nodes" key is examined for
a list of nodes in the cluster: if it is empty, then the new node becomes the
master. Otherwise, the node becomes a standby, examines the priority setting
of all the existing nodes, and chooses a priority lower than all the other nodes.

During operation, when a node's state changes (eg. a standby transitions to
master, after a previous master failure), a notify script updates the node
info in consul, to reflect the new state.
This info isn't currently used, but could be used to eg. make sure that the
server holding the virtual IP is also the current database master.


.. note:: Keepalived - IaaS specific

    Keepalived only manages a LVS virtual IP. In practice, this means the
    virtual IP can only come from a local network that the server can broadcast
    ARP to, it can't be eg. an openstack floating IP. To use keepalived with
    openstack, you need to create an openstack port that will connect a floating
    IP to a fixed IP in the local network, and use that fixed IP with keepalived.


Postgresql
----------

There are three elements to postgresql HA: replication, monitoring, and proxying.
For replication, we use repmgr (`repmgr home page <http://www.repmgr.org/>`_),
which is a system built on postgresql's own replication mechanisms, and
implements failover.

During configuration, the cluster state in consul is examined, and if there's
no master registered yet, the new machine becomes the master. Otherwise, it
becomes a replica, taking the master's connection info from consul.
On replicas, repmgr immediately clones the data from master during configuration,
and sets up streaming replication.

For monitoring, we use repmgrd, which is repmgr's monitoring daemon. Repmgrd
runs on each machine in the cluster, and monitors the state of the current
master. If the master server doesn't respond, it chooses one of the replicas
to become the new master. When a replica is promoted to master, the cluster
state in consul is updated to reflect the new master, and all the other replicas
switch to following it.

Proxying isn't strictly necessary if we can guarantee that all requests will
only go to the server which is the database master, but is required if a request
is handled on a machine that is a database replica; or in case of partial master
failure (eg. only postgresql on the master server goes down, but the REST
service doesn't).
Each machine runs pgbouncer which is configured using the current cluster state
from consul to proxy to the current master server. This allows the REST service
on each machine to connect to localhost, and be sure that the queries will be
routed to the current master server.
This also allows limited partition tolerance (where agents can't connect to the
master due to network failure, but can connect to a replica), and in the future
will allow load-balancing in the cluster.


.. note:: Repmgr vs stolon vs others

    Repmgr+pgbouncer were chosen because of their good balance between being
    feature-rich, but still configurable. Repmgr makes the cluster setup
    almost automatic, but still allows manual reconfiguration (moving the master,
    removing nodes from the cluster). Other examined solutions were: stolon
    (easier to set up, and comes with the proxy built-in, but control is very
    limited: no reconfiguration), and plain postgresql replication (tricky to
    get right for more than 2 machines, and we would end up reimplementing
    repmgr; also needs a separate proxy)


Syncthing
---------

For filesystem replication, `syncthing <https://syncthing.net/>`_ is used.
During configuration, each node adds its address and ID to consul, and at runtime,
each node examines the data stored in consul to discover other manager machines
running syncthing.

Syncthing runs as a service on each machine, transparently replicating files
in configured directories to all the other machines.

Currently, the following directories are replicated:

    - `/opt/manager/resources` - holds the blueprints uploaded by the user
    - `/opt/mgmtworker/env/plugins` - holds plugins installed on the manager.
      This is required so that doing `cfy plugins upload` will install the plugin
      on all machines in the cluster.

.. warning:: Asynchronous replication

    Note that currently the replication is asynchronous, ie. it happens in the
    background, some time after first uploading the files to one of the machines
    (configurable, on the order of 10 seconds). Unfortunately, this means that if
    the master manager goes down in the few seconds after uploading a blueprint or
    a plugin, it is unknown whether or not this blueprint/plugin was replicated
    successfully to the other machines, and needs to be uploaded again.

    To change this, we'll need poll the syncthing API after uploading any
    resources, and only report success after the data was replicated.


RabbitMQ
--------

RabbitMQ is not replicated. This means that the REST service on every machine
will connect to RabbitMQ on localhost, and only the mgmtworker on that machine
will run the operations. This never leaves the system in an ambiguous state,
but doesn't allow load balancing. In the future, we might use RabbitMQ's
clustering feature, but this will also require a distributed lock, so that
no task is executed twice (this might be implemented on top of consul).


Elasticsearch
-------------

Elasticsearch (storing logs and events) is currently not replicated. This means
that after the master manager goes down, logs that were stored on it are lost.
