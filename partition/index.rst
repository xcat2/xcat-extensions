Configure RAID before deploying the OS
======================================

This script ./raid1_rh.sh can be used to setup RAID1 on 2 disks on Power8 LE server, it is composed of 2 parts:

    the logic to select the disks to setup RAID
    the logic to generate the partition scheme and save it to /tmp/partitionfile in the installer.

