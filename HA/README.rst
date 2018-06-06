Shared data based xCAT HA MN
============================

#. Setup this node be the shared data based xCAT MN::

   xcatha.py -s|--setup -p <shared-data directory path> -i <nic> -v <virtual ip> -n <virtual IP hostname> [-m <netmask>] [-t <database type>] [--dryrun]

#. Activate this node to be the shared data based xCAT MN:: 

   xcatha.py -a|--activate -p <shared-data directory path> -i <nic> -v <virtual ip> [-m <netmask>] [-t <database type>] [--dryrun]

#. Deactivate this node to be the shared data based xCAT MN::

   xcatha.py -d|--deactivate -i <nic> -v <virtual ip> [--dryrun]

