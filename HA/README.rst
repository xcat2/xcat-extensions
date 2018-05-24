Shared data based xCAT HA MN
============================

1, Setup this node be the shared data based xCAT MN::

   xcatha_setup.py -p <shared-data directory path> -i <nic> -v <virtual ip> -n <virtual IP hostname> [-m <netmask>] [-t <database type>]

2, Activate this node to be the shared data based xCAT MN:: 

   xcatha_failover.py -a|--activate -p <shared-data directory path> -i <nic> -v <virtual ip> [-m <netmask>] [-t <database type>]

3, Deactivate this node to be the shared data based xCAT MN::

   xcatha_failover.py -d|--deactivate -i <nic> -v <virtual ip>

