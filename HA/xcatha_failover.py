#!/usr/bin/env python
###############################################################################
# IBM(c) 2018 EPL license http://www.eclipse.org/legal/epl-v10.html
###############################################################################
# -*- coding: utf-8 -*-
#  CHANGE HISTORY:
#   
#  NAME:  xcatha_failover.py
#
#  SYNTAX: xcatha_failover.py -a|--activate -p <shared-data directory path> -i <nic> -v <virtual ip> [-m <netmask>] [-t <database type>] 
#  SYNTAX: xcatha_failover.py -d|--deactivate -i <nic> -v <virtual ip>
#
#  DESCRIPTION:  Activate/Deactivate this node to be the shared data based xCAT MN
#
#  FLAGS:
#               -p      the shared data directory path
#               -i      the nic that the virtual ip address attaches to,
#                       for Linux, it could be eth0:1 or eth1:2 or ...
#               -v      virtual ip address
#               -m      netmask for the virtual ip address,
#                       default to 255.255.255.0
#               -n      virtual ip hostname, default ?
#               -t      target database type, it can be postgresql, default is sqlite
import argparse
from xcatha_setup import xcat_ha_utils, HaException

def parse_arguments():
    """parse input arguments"""
    parser = argparse.ArgumentParser(description="Activate/Deactivate shared data based xCAT HA MN node")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-a', '--activate', help="activate node to be xCAT MN", action='store_true')
    group.add_argument('-d', '--deactivate', help="deactivate node to be xCAT MN", action='store_true')

    parser.add_argument('-v', dest="virtual_ip", required=True, help="virtual IP")
    parser.add_argument('-i', dest="nic", required=True, help="virtual IP network interface")

    parser.add_argument('-p', dest="path", help="shared data directory path")
    parser.add_argument('-n', dest="host_name", help="virtual IP hostname")
    parser.add_argument('-m', dest="netmask", help="virtual IP network mask")
    parser.add_argument('-t', dest="dbtype", choices=['postgresql', 'sqlite'], help="database type")
    args = parser.parse_args()
    return args

def main():
    args=parse_arguments()
    obj=xcat_ha_utils()
    try:
        if args.activate:
            if args.path:
                print "Option -p is not valid for xCAT MN deactivation"
            if not args.netmask:
                args.netmask="255.255.255.0"
            if not args.dbtype:
                args.dbtype="sqlite"
            if not args.host_name:
                print "Argument -n is required"
                return

            print "Activating this node as xCAT MN"
            obj.activate_management_node(args.nic, args.virtual_ip, args.dbtype, args.path, args.host_name, args.netmask)
        if args.deactivate:
            if args.dbtype:
                print "Option -t is not valid for xCAT MN deactivation"
                return
            if args.netmask:
                print "Option -m is not valid for xCAT MN deactivation"
                return
            if args.host_name:
                print "Option -n is not valid for xCAT MN deactivation"
                return

            print "Deactivating this node as xCAT MN"
            dbtype=obj.current_database_type("")
            obj.deactivate_management_node(args.nic, args.virtual_ip, dbtype)

    except HaException,e:
        error_msg="=================="+e.message+"=================================="
        print error_msg        
        print "Error encountered, starting to clean up the environment"
        obj.clean_env(args.virtual_ip, args.nic, args.host_name)

if __name__ == "__main__":
    main()
