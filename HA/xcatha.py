#!/usr/bin/env python
###############################################################################
# IBM(c) 2018 EPL license http://www.eclipse.org/legal/epl-v10.html
###############################################################################
# -*- coding: utf-8 -*-
#  CHANGE HISTORY:
#   
#  NAME:  xcatha.py
#
#  SYNTAX: xcatha.py -s|--setup -p <shared-data directory path> -i <nic> -v <virtual ip> -n <virtual ip hostname> [-m <netmask>] [-t <database type>] 
#
#  SYNTAX: xcatha.py -a|--activate -p <shared-data directory path> -i <nic> -v <virtual ip> [-m <netmask>] [-t <database type>]
#
#  SYNTAX: xcatha.py -d|--deactivate -i <nic> -v <virtual ip>
#
#  DESCRIPTION:  Setup/Activate/Deactivate this node be the shared data based xCAT MN
#
#  FLAGS:
#               -p      the shared data directory path
#               -i      the nic that the virtual ip address attaches to,
#                       for Linux, it could be eth0:1 or eth1:2 or ...
#               -v      virtual ip address
#               -n      virtual ip hostname
#               -m      netmask for the virtual ip address,
#                       default to 255.255.255.0
#               -t      target database type, it can be postgresql, default is sqlite
import argparse
import os
import time
import platform
import shutil
import logging
from subprocess import Popen, PIPE
import pdb

xcat_url="https://raw.githubusercontent.com/xcat2/xcat-core/master/xCAT-server/share/xcat/tools/go-xcat"
shared_fs=['/install','/etc/xcat','/root/.xcat','/var/lib/pgsql','/tftpboot']
xcat_cfgloc="/etc/xcat/cfgloc"
xcat_install="/tmp/go-xcat --yes install"
xcatdb_password="XCATPGPW=cluster"
setup_process_msg=""

#configure logger
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
DATE_FORMAT = "%m/%d/%Y %H:%M:%S %p"
logging.basicConfig(filename = os.path.join(os.getcwd(), 'xcatha.log'), level = logging.INFO, filemode = 'a', format = LOG_FORMAT, datefmt=DATE_FORMAT)
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter(LOG_FORMAT))
logger = logging.getLogger('xCAT-HA')
logger.addHandler(console_handler)


class HaException(Exception):
    """customize exception"""
    def __init__(self,message):
        Exception.__init__(self)
        self.message=message

class xcat_ha_utils:
    """"""
    def log_info(self, message):
        """print format"""
        print "============================================================================================"
        logger.info(message)

    def vip_check(self, vip):
        """check if virtual ip can ping or not"""
        global setup_process_msg
        setup_process_msg="Check virtual ip stage"
        self.log_info(setup_process_msg)
        cmd="ping -c 1 -w 10 "+vip
        logger.info(cmd)
        res=os.system(cmd)
        if res is 0:
            message="Aborted startup as virtual ip appears to be already active."
            logger.error(message)
            raise HaException("Error: "+setup_process_msg)    
        else:
            message="virtual ip can be used."
            logger.info(message)

    def execute_command(self, cmd, retry):
        """execute and retry execute command"""
        loginfo="Running "+cmd
        logger.info(loginfo)
        a=0
        while True:
            res=os.system(cmd)
            if res is 0:
                loginfo=cmd+" [passed]"
                logger.info(cmd)
                return 0
            else:
                if retry is 0:
                    loginfo=cmd+" [Failed]"
                    logger.error(loginfo)
                    return 1
                a += 1
                if a < retry:
                    time.sleep(3)
                    loginfo="Retry "+bytes(a)+" ... ..."+cmd
                    logger.info(loginfo)       
            if a==3:
                loginfo=cmd+" [Failed]"
                logger.error(loginfo)
                return 1

    def configure_xcat_attribute(self, host, ip):
        "configure xcat MN attribute"
        self.log_info("Configure xCAT management node attribute")
        pass

    def current_database_type(self, path):
        """current data base type"""
        cfgloc=path+xcat_cfgloc
        if os.path.exists(cfgloc):
            with open(cfgloc, 'r') as file:
                cdbtype=file.read(2)
            file.close()
            if cdbtype == 'my':
                current_data_db="mysql"
            else:
                current_data_db="postgresql"
        else:
            current_data_db="sqlite"
        return current_data_db

    def get_physical_ip(self, nic):
        """get physical ip"""
        main_nic=nic.split(":")[0]
        f=Popen(('ifconfig',main_nic), stdout=PIPE).stdout
        data=[eachLine.strip() for eachLine in f]
        physical_ip=filter(lambda x : 'inet ' in x, data)[0].split(" ")[1]
        return physical_ip 

    def check_database_type(self, dbtype, vip, nic):
        """if current xcat DB type is different from target type, switch DB to target type"""
        global setup_process_msg
        setup_process_msg="Check database type stage"
        self.log_info(setup_process_msg)
        current_dbtype=self.current_database_type("")
        logger.info("current xCAT database type: "+current_dbtype)
        logger.info("target xCAT database type: "+dbtype)
        target_dbtype="dbengine=dbtype"
        if current_dbtype != target_dbtype:
            physical_ip=self.get_physical_ip(nic)
            self.switch_database(dbtype,vip,physical_ip)

    def check_xcat_exist_in_shared_data(self, path):
        """check if xcat data is in shared data directory"""
        global setup_process_msg
        setup_process_msg="check if xcat data is in shared data directory"
        self.log_info(setup_process_msg)
        xcat_path=path+"/install"
        if os.path.exists(xcat_path):
            logger.info("There is xCAT data "+xcat_path+" in shared data "+path)
            return 1
        else:
            logger.error("There is no xCAT data "+xcat_path+" in shared data "+path)
            return 0

    def check_shared_data_db_type(self, tdbtype, path):
        """check if target dbtype is the same with shared data dbtype"""
        global setup_process_msg
        setup_process_msg="Check if target dbtype is the same with shared data dbtype stage"
        self.log_info(setup_process_msg)
        cfgfile=path+xcat_cfgloc
        share_data_db=""
        if os.path.exists(cfgfile):
            with open(cfgfile,'r') as file:
                sdbtype=file.read(2)
            file.close()
            if sdbtype == 'my':
                share_data_db="mysql"
            elif sdbtype == 'Pg':
                share_data_db="postgresql"
        else:
            share_data_db="sqlite"
        logger.info("database type is '"+share_data_db+"' in shared data directory")
        if share_data_db == tdbtype:
            logger.info("target database type is matched [Passed]")
        else:
            logger.error("Error: target database is not matched [Failed]")
            raise HaException("Error: "+setup_process_msg)
        
    def switch_database(self, dbtype, vip, physical_ip):
        """switch database to target type"""
        global setup_process_msg
        res=self.install_db_package(dbtype)
        if res is 0:
            setup_process_msg="Switch to target database stage"
            self.log_info(setup_process_msg)
            if dbtype == "postgresql":
                cmd="export "+xcatdb_password+";pgsqlsetup -i -a "+vip+" -a "+physical_ip
                res=self.execute_command(cmd,0)
                if res is 0:
                    logger.info("Switch to "+dbtype+" [Passed]")
                else:
                    logger.error("Switch to "+dbtype+" [Failed]")
            else:
                logger.error("Do not support"+dbtype+" [Failed]")  
 
    def install_db_package(self, dbtype):
        """install database package"""
        global setup_process_msg
        setup_process_msg="Install database package stage"
        self.log_info("Install database package ...")
        os_name=platform.platform()
        if os_name.__contains__("redhat") and dbtype== "postgresql":  
            cmd="yum -y install postgresql* perl-DBD-Pg"
            res=self.execute_command(cmd,0)
            if res is not 0:
                logger.error("install postgresql* perl-DBD-Pg  package [Failed]")
            else:
                logger.info("install postgresql* perl-DBD-Pg  package [Passed]")     
            return res

    def install_xcat(self, url):
        """install stable xCAT"""
        global setup_process_msg
        setup_process_msg="Install xCAT stage"
        self.log_info(setup_process_msg)
        cmd="wget "+url+" -O - >/tmp/go-xcat"
        res=self.execute_command(cmd,0)
        if res is 0:
            cmd="chmod +x /tmp/go-xcat"
            res=self.execute_command(cmd,0)
            if res is 0:
                cmd=xcat_install
                res=self.execute_command(cmd,0)
                if res is 0:
                    print "xCAT is installed [Passed]"
                    xcat_env="/opt/xcat/bin:/opt/xcat/sbin:/opt/xcat/share/xcat/tools:"
                    os.environ["PATH"]=xcat_env+os.environ["PATH"]
                    cmd="lsxcatd -v"
                    self.execute_command(cmd,0)
                    return 1
                else:
                    logger.error("xCAT is installed [Failed]")
            else:
                logger.error("chmod [Failed]")
        else:
            logger.error("wget [Failed]")
        
            
    def configure_vip(self, vip, nic, mask):
        """configure virtual ip"""
        global setup_process_msg
        setup_process_msg="Start configure virtual ip as alias ip stage"
        self.log_info(setup_process_msg)
        cmd="ifconfig "+nic+" "+vip+" "+" netmask "+mask
        res=self.execute_command(cmd,0)
        if res is 0:
            message="configure virtual IP [passed]."
            logger.info(message)
        else :
            message="Error: configure virtual IP [failed]."
            logger.error(message) 
            raise HaException("Error: "+setup_process_msg)
        #add virtual ip into /etc/resolve.conf
        msg="add virtual ip "+vip+" into /etc/resolv.conf"
        self.log_info(msg)
        name_server="nameserver "+vip
        resolv_file="/etc/resolv.conf"
        res=self.find_line(resolv_file, name_server)
        if res is False:
            resolvefile=open(resolv_file,'a')
            print name_server
            resolvefile.write(name_server)
            resolvefile.close()

    def find_line(self, filename, keyword):
        """find keyword from file"""
        with open(filename,'r')as fp:
            list1 = fp.readlines()
            for line in list1:
                line=line.rstrip('\n')
                if keyword in line:
                    return 1
        return 0
 
    def change_hostname(self, host, ip):
        """change hostname"""
        global setup_process_msg
        setup_process_msg="Start configure hostname stage"
        self.log_info(setup_process_msg)
        ip_and_host=ip+" "+host
        hostfile="/etc/hosts"
        res=self.find_line(hostfile, ip_and_host)
        if res is False:
            hostfile=open(hostfile,'a')
            hostfile.write(ip_and_host)
            hostfile.close()
        cmd="hostname "+host
        res=self.execute_command(cmd,0)
        if res is 0:
            logger.info(cmd+" [Passed]")
        else:
            logger.error(cmd+" [Failed]")

    def unconfigure_vip(self, vip, nic):
        """remove vip from nic and /etc/resolve.conf"""
        global setup_process_msg
        setup_process_msg="remove virtual ip"
        self.log_info(setup_process_msg)
        cmd="ifconfig "+nic+" 0.0.0.0 0.0.0.0 &>/dev/null"
        res=self.execute_command(cmd,0)
        cmd="ip addr show |grep "+vip+" &>/dev/null"
        res=self.execute_command(cmd,0)
        if res is 0:
            logger.errer("remove virtual IP [Failed]")
            raise HaException("Error: "+setup_process_msg)
        else:
            logger.info("Remove virtual IP [Passed]")
           
    def check_service_status(self, service_name):
        """check service status"""
        global setup_process_msg
        setup_process_msg="Check "+service_name+" service status"
        self.log_info(setup_process_msg)
        cmd="systemctl status "+service_name+" > /dev/null"
        status =self.execute_command(cmd,0)
        return status

    def finditem(self, n, server):
        """add item into policy table"""
        index=bytes(n)
        cmd="lsdef -t policy |grep 1."+index
        res=self.execute_command(cmd,0)
        if res is not 0:
            cmd="chdef -t policy 1."+index+" name="+server+" rule=trusted"
            res=self.execute_command(cmd,0)
            if res is 0:
                loginfo="'"+cmd+"' [Passed]"
                logger.info(loginfo)
                return 0
            else:
                loginfo="'"+cmd+"' [Failed]"
                logger.error(loginfo)
                return 1
        else:
            n+=1
            finditem(bytes(n),server)

    def change_xcat_policy_attribute(self, nic, vip):
        """add hostname into policy table"""
        global setup_process_msg
        setup_process_msg="Configure xCAT policy table stage"
        self.log_info(setup_process_msg)
        filename="/etc/xcat/cert/server-cert.pem"
        word="Subject: CN="
        server=""
        with open(filename, 'r') as f:
            for l in f.readlines():
                if word in l:
                    linelist=l.split("=")
                    server=linelist[1].strip()
                    break
        if server:
            cmd="lsdef -t policy -i name|grep "+server
            res=self.execute_command(cmd,0)
            if res is not 0:
                res=self.finditem(3,server)
                if res is 0:
                    return 0
            else:
                loginfo=server+" exist in policy table."
                logger.info(loginfo)
                return 0
        else:
            loginfo="get server name "+server+" [Failed]" 
            logger.error(loginfo)
        return 1       

    def copy_files(self, sourceDir, targetDir):  
        print sourceDir  
        for f in os.listdir(sourceDir):  
            sourceF = os.path.join(sourceDir, f)  
            targetF = os.path.join(targetDir, f)  
                
            if os.path.isfile(sourceF):  
                #create dir 
                if not os.path.exists(targetDir):  
                    os.makedirs(targetDir)  
              
                #if file does not exist, or size is different, overwrite
                if not os.path.exists(targetF) or (os.path.exists(targetF) and (os.path.getsize(targetF) != os.path.getsize(sourceF))):  
                    #binary
                    open(targetF, "wb").write(open(sourceF, "rb").read())  
                    print u"%s copy complete" %(targetF)  
                else:  
                    print u"%s existed, do not copy it" %(targetF)  
            if os.path.isdir(sourceF):  
                self.copy_files(sourceF, targetF)


    def configure_shared_data(self, path, sharedfs):
        """configure shared data directory"""
        global setup_process_msg
        setup_process_msg="Configure shared data directory stage"
        self.log_info(setup_process_msg)
        #check if there is xcat data in shared data directory
        xcat_file_path=path+"/etc/xcat"
        if not os.path.exists(xcat_file_path):
            permision=oct(os.stat(path).st_mode)[-3:]           
            if permision == '755':
                i = 0
                while i < len(sharedfs):
                    xcat_file_path=path+sharedfs[i]
                    if not os.path.exists(xcat_file_path):
                        os.makedirs(xcat_file_path)
                    self.copy_files(sharedfs[i],xcat_file_path)
                    i += 1  
        #create symlink 
        i=0
        while i < len(sharedfs):
            logger.info("create symlink ..."+sharedfs[i])
            xcat_file_path=path+sharedfs[i]
            if not os.path.islink(sharedfs[i]):
                if os.path.exists(sharedfs[i]):
                    shutil.move(sharedfs[i], sharedfs[i]+".xcatbak")
                os.symlink(xcat_file_path, sharedfs[i])     
            i += 1

    def unconfigure_shared_data(self, sharedfs):
        """unconfigure shared data directory"""
        global setup_process_msg
        setup_process_msg="Unconfigure shared data directory stage"
        self.log_info(setup_process_msg)
        #1.check if there is xcat data in shared data directory
        #2.unlink data in shared data directory
        i=0
        while i < len(sharedfs):
            logger.info("remove symlink ..."+sharedfs[i])
            if os.path.islink(sharedfs[i]):
                os.unlink(sharedfs[i])     
            i += 1

    def clean_env(self, vip, nic, host):
        """clean up env when exception happen"""
        self.unconfigure_shared_data(shared_fs)
        self.unconfigure_vip(vip, nic)

    def deactivate_management_node(self, nic, vip, dbtype):
        """deactivate management node"""
        global setup_process_msg
        setup_process_msg="Deactivate stage"
        self.log_info(setup_process_msg)
        self.execute_command("chkconfig --level 345 xcatd off",3)
        self.execute_command("chkconfig --level 2345 conserver off",3)
        self.execute_command("chkconfig --level 2345 dhcpd off",3)
        self.execute_command("chkconfig postgresql off",3)
        self.execute_command("service conserver stop",3)
        self.execute_command("service dhcpd stop",3)
        self.execute_command("service named stop",3)
        self.execute_command("service xcatd stop",3)
        stop_db="service "+dbtype+" stop"
        self.execute_command(stop_db,3)
        self.execute_command("service ntpd restart",3)
        self.unconfigure_shared_data(shared_fs)
        self.unconfigure_vip(vip, nic)
 
    def activate_management_node(self, nic, vip, dbtype, path, hostname, mask):
        """activate management node"""
        global setup_process_msg
        setup_process_msg="Activate stage"
        self.log_info(setup_process_msg)
        self.execute_command("chkconfig --level 345 xcatd off",3)
        self.execute_command("chkconfig --level 2345 conserver off",3)
        self.execute_command("chkconfig --level 2345 dhcpd off",3)
        self.execute_command("chkconfig postgresql off",3)
        self.execute_command("service conserver start",3)
        self.execute_command("service dhcpd start",3)
        self.execute_command("service named start",3)
        self.execute_command("service xcatd start",3)
        start_db="service "+dbtype+" start"
        self.execute_command(start_db,3)
        self.execute_command("service ntpd restart",3)
        self.change_hostname(host_name,args.vip)
        self.configure_shared_data(args.path, shared_fs)
        self.configure_vip(vip, nic)
 
    def xcatha_setup_mn(self, args):
        """setup_mn process"""
        try:
            self.vip_check(args.virtual_ip)
            if self.check_xcat_exist_in_shared_data(args.path):
                self.check_shared_data_db_type(args.dbtype,args.path)
            if self.configure_vip(args.virtual_ip,args.nic,args.netmask):
                return 1
            self.change_hostname(args.host_name,args.virtual_ip)
            if self.check_service_status("xcatd") is not 0:
                self.install_xcat(xcat_url)
            self.check_database_type(args.dbtype,args.virtual_ip,args.nic)
            self.configure_shared_data(args.path, shared_fs)
            if self.check_service_status("xcatd") is not 0:
                logger.error("xCAT service does not work well [Failed]")
                raise HaException("Error: "+setup_process_msg)
            else:
                logger.info("xCAT service works well [Passed]")
            self.change_xcat_policy_attribute(args.nic, args.virtual_ip)
            self.deactivate_management_node(args.nic, args.virtual_ip, args.dbtype) 
            logger.info("This machine is set to standby management node successfully...")
        except:
            raise HaException("Error: "+setup_process_msg)

def parse_arguments():
    """parse input arguments"""
    parser = argparse.ArgumentParser(description="Setup/Activate/Deactivate shared data based xCAT HA MN node")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-s', '--setup', help="setup node to be xCAT MN", action='store_true')
    group.add_argument('-a', '--activate', help="activate node to be xCAT MN", action='store_true')
    group.add_argument('-d', '--deactivate', help="deactivate node to be xCAT MN", action='store_true')

    parser.add_argument('-p', dest="path", required=True, help="shared data directory path")
    parser.add_argument('-v', dest="virtual_ip", required=True, help="virtual IP")
    parser.add_argument('-i', dest="nic", required=True, help="virtual IP network interface")
    parser.add_argument('-n', dest="host_name", required=True, help="virtual IP hostname")
    parser.add_argument('-m', dest="netmask", default="255.255.255.0", help="virtual IP network mask")
    parser.add_argument('-t', dest="dbtype", default="sqlite", choices=['postgresql', 'sqlite'], help="database type")
    args = parser.parse_args()
    return args

def main():
    args=parse_arguments()
    obj=xcat_ha_utils()
    try:
        if args.activate:
            if args.path:
                logger.error("Option -p is not valid for xCAT MN deactivation")
                return
            if not args.netmask:
                args.netmask="255.255.255.0"
            if not args.dbtype:
                args.dbtype="sqlite"
            if not args.host_name:
                logger.error("Argument -n is required")
                return

            obj.log_info("Activating this node as xCAT MN")
            obj.activate_management_node(args.nic, args.virtual_ip, args.dbtype, args.path, args.host_name, args.netmask)

        if args.deactivate:
            if args.dbtype:
                logger.error("Option -t is not valid for xCAT MN deactivation")
                return 1
            if args.netmask:
                logger.error("Option -m is not valid for xCAT MN deactivation")
                return 1
            if args.host_name:
                logger.error("Option -n is not valid for xCAT MN deactivation")
                return 1

            obj.log_info("Deactivating this node as xCAT MN")
            dbtype=obj.current_database_type("")
            obj.deactivate_management_node(args.nic, args.virtual_ip, dbtype)

        if args.setup:
            if not args.netmask:
                args.netmask="255.255.255.0"
            if not args.dbtype:
                args.dbtype="sqlite"
            res=obj.xcatha_setup_mn(args)
            if res:
                
                obj.clean_env(args.virtual_ip, args.nic, args.host_name)            
    except HaException,e:
        logger.error(e.message)
        logger.error("Error encountered, starting to clean up the environment")
        obj.clean_env(args.virtual_ip, args.nic, args.host_name)

if __name__ == "__main__":
    main()
