#!/usr/bin/env python
###############################################################################
# IBM(c) 2018 EPL license http://www.eclipse.org/legal/epl-v10.html
###############################################################################
# -*- coding: utf-8 -*-
#  CHANGE HISTORY:
#   
#  NAME:  xcatha_setup.py
#
#  SYNTAX: xcatha_setup.py -p <shared-data directory path> -i <nic> -v <virtual ip> -n <virtual ip hostname> [-m <netmask>] [-t <database type>] 
#
#  DESCRIPTION:  Setup this node be the shared data based xCAT MN
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
from subprocess import Popen, PIPE
import pdb

xcat_url="https://raw.githubusercontent.com/xcat2/xcat-core/master/xCAT-server/share/xcat/tools/go-xcat"
shared_fs=['/install','/etc/xcat','/root/.xcat','/var/lib/pgsql','/tftpboot']
xcat_cfgloc="/etc/xcat/cfgloc"
xcat_install="/tmp/go-xcat --yes install"
xcatdb_password="XCATPGPW=cluster"
setup_process_msg=""

class HaException(Exception):
    def __init__(self,message):
        Exception.__init__(self)
        self.message=message

class xcat_ha_utils:

    def log_info(self, message):
        print "============================================================================================"
        print message

    def runcmd(self, cmd):
        """print and execute command"""
        print cmd
        res=os.system(cmd)
        return res

    def vip_check(self, vip):
        """check if virtual ip can ping or not"""
        global setup_process_msg
        setup_process_msg="Check virtual ip stage"
        self.log_info(setup_process_msg)
        pingcmd="ping -c 1 -w 10 "+vip
        res=self.runcmd(pingcmd)
        if res is 0:
            message="Error: Aborted startup as virtual ip appears to be already active."
            self.log_info(message)
            exit(1)
        else:
            message="virtual ip can be used [Passed]"
            print message

    def execute_command(self, cmd):
        """execute and retry execute command"""
        loginfo="Running command:"+cmd
        print loginfo
        a=0
        while True:
            res=os.system(cmd)
            if res is 0:
                loginfo=cmd+" [Passed]"
                return 0
            else:
                a += 1
                if a < 3:
                    time.sleep(3)
                    loginfo="Retry "+bytes(a)+" ... ..."+cmd
                    print loginfo       
            if a==3:
                loginfo=cmd+" [Failed]"
                print loginfo
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
        print "current xCAT database type: "+current_dbtype
        print "target xCAT database type: "+dbtype
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
            print "There is xCAT data "+xcat_path+" in shared data "+path
            return True
        else:
            print "There is no xCAT data "+xcat_path+" in shared data "+path
            return False

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
        print "database type is '"+share_data_db+"' in shared data directory"
        if share_data_db == tdbtype:
            print "target database type is matched [Passed]"
        else:
            print "Error: target database is not matched [Failed]"
            exit(1)
        
    def switch_database(self, dbtype, vip, physical_ip):
        """switch database to target type"""
        global setup_process_msg
        res=self.install_db_package(dbtype)
        if res is 0:
            setup_process_msg="Switch to target database stage"
            self.log_info(setup_process_msg)
            if dbtype == "postgresql":
                cmd="export "+xcatdb_password+";pgsqlsetup -i -a "+vip+" -a "+physical_ip
                res=self.runcmd(cmd)
                if res is 0:
                    print "Switch to "+dbtype+" [Passed]"
                else:
                    print "Switch to "+dbtype+" [Failed]"
            else:
                print "Do not support"+dbtype+" [Failed]"  
 
    def install_db_package(self, dbtype):
        """install database package"""
        global setup_process_msg
        setup_process_msg="Install database package stage"
        self.log_info("Install database package ...")
        os_name=platform.platform()
        if os_name.__contains__("redhat") and dbtype== "postgresql":  
            cmd="yum -y install postgresql* perl-DBD-Pg"
            res=self.runcmd(cmd)
            if res is not 0:
                print "install postgresql* perl-DBD-Pg  package [Failed]"
            else:
                print "install postgresql* perl-DBD-Pg  package [Passed]"     
            return res

    def install_xcat(self, url):
        """install stable xCAT"""
        global setup_process_msg
        setup_process_msg="Install xCAT stage"
        self.log_info(setup_process_msg)
        cmd="wget "+url+" -O - >/tmp/go-xcat"
        res=self.runcmd(cmd)
        if res is 0:
            cmd="chmod +x /tmp/go-xcat"
            res=self.runcmd(cmd)
            if res is 0:
                cmd=xcat_install
                res=self.runcmd(cmd)
                if res is 0:
                    print "xCAT is installed [Passed]"
                    xcat_env="/opt/xcat/bin:/opt/xcat/sbin:/opt/xcat/share/xcat/tools:"
                    os.environ["PATH"]=xcat_env+os.environ["PATH"]
                    cmd="lsxcatd -v"
                    self.runcmd(cmd)
                    return True
                else:
                    print "xCAT is installed [Failed]"
            else:
                print "chmod [Failed]"
        else:
            print "wget [Failed]"
        return False
            
    def configure_vip(self, vip, nic, mask):
        """configure virtual ip"""
        global setup_process_msg
        setup_process_msg="Start configure virtual ip as alias ip stage"
        self.log_info(setup_process_msg)
        cmd="ifconfig "+nic+" "+vip+" "+" netmask "+mask
        res=self.runcmd(cmd)
        if res is 0:
            message="configure virtual IP [passed]."
            print message
        else :
            message="Error: configure virtual IP [failed]."
            print message 
            exit(1)
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
                    return True
        return False
 
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
        res=self.runcmd(cmd)
        if res is 0:
            print cmd+" [Passed]"
        else:
            print cmd+" [Failed]"


    def unconfigure_vip(self, vip, nic):
        """remove vip from nic and /etc/resolve.conf"""
        global setup_process_msg
        setup_process_msg="remove virtual ip"
        self.log_info(setup_process_msg)
        cmd="ifconfig "+nic+" 0.0.0.0 0.0.0.0 &>/dev/null"
        res=self.runcmd(cmd)
        cmd="ip addr show |grep "+vip+" &>/dev/null"
        res=self.runcmd(cmd)
        if res is 0:
            print "Error: fail to remove virtual IP"
            exit(1)
        else:
            print "Remove virtual IP [Passed]"

    def check_service_status(self, service_name):
        """check service status"""
        global setup_process_msg
        setup_process_msg="Check "+service_name+" service status"
        self.log_info(setup_process_msg)
        status =self.runcmd('systemctl status '+service_name+ ' > /dev/null')
        return status

    def finditem(self, n, server):
        """add item into policy table"""
        index=bytes(n)
        cmd="lsdef -t policy |grep 1."+index
        res=self.runcmd(cmd)
        if res is not 0:
            cmd="chdef -t policy 1."+index+" name="+server+" rule=trusted"
            res=self.runcmd(cmd)
            if res is 0:
                loginfo="'"+cmd+"' [Passed]"
                print loginfo
                return 0
            else:
                loginfo="'"+cmd+"' [Failed]"
                print loginfo
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
            res=self.runcmd(cmd)
            if res is not 0:
                res=self.finditem(3,server)
                if res is 0:
                    return 0
            else:
                loginfo=server+" exist in policy table."
                return 0
        else:
            loginfo="Error: get server name "+server+" failed." 
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
                    print u"%s %s copy complete" %(time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time())), targetF)  
                else:  
                    print u"%s %s existed, do not copy it" %(time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time())), targetF)  
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
            print "create symlink ..."+sharedfs[i]
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
            print "remove symlink ..."+sharedfs[i]
            if os.path.islink(sharedfs[i]):
                os.unlink(xcat_file_path, sharedfs[i])     
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
        self.execute_command("chkconfig --level 345 xcatd off")
        self.execute_command("chkconfig --level 2345 conserver off")
        self.execute_command("chkconfig --level 2345 dhcpd off")
        self.execute_command("chkconfig postgresql off")
        self.execute_command("service conserver stop")
        self.execute_command("service dhcpd stop")
        self.execute_command("service named stop")
        self.execute_command("service xcatd stop")
        stop_db="service "+dbtype+" stop"
        self.execute_command(stop_db)
        self.execute_command("service ntpd restart")
        self.unconfigure_shared_data(shared_fs)
        self.unconfigure_vip(vip, nic)
 
    def activate_management_node(self, nic, vip, dbtype, path, hostname, mask):
        """activate management node"""
        global setup_process_msg
        setup_process_msg="Activate stage"
        self.log_info(setup_process_msg)
        self.execute_command("chkconfig --level 345 xcatd off")
        self.execute_command("chkconfig --level 2345 conserver off")
        self.execute_command("chkconfig --level 2345 dhcpd off")
        self.execute_command("chkconfig postgresql off")
        self.execute_command("service conserver start")
        self.execute_command("service dhcpd start")
        self.execute_command("service named start")
        self.execute_command("service xcatd start")
        start_db="service "+dbtype+" start"
        self.execute_command(start_db)
        self.execute_command("service ntpd restart")
        self.change_hostname(host_name,args.vip)
        self.configure_shared_data(args.path, shared_fs)
        self.configure_vip(vip, nic)
 
    def xcatha_setup_mn(self, args):
        """setup_mn process"""
        try:
            self.vip_check(args.virtual_ip)
            if self.check_xcat_exist_in_shared_data(args.path):
                self.check_shared_data_db_type(args.dbtype,args.path)
            self.configure_vip(args.virtual_ip,args.nic,args.netmask)
            self.change_hostname(args.host_name,args.virtual_ip)
            if self.check_service_status("xcatd") is not 0:
                self.install_xcat(xcat_url)
            self.check_database_type(args.dbtype,args.virtual_ip,args.nic)
            self.configure_shared_data(args.path, shared_fs)
            if self.check_service_status("xcatd") is not 0:
                print "Error: xCAT service does not work well [Failed]"
                exit(1)
            else:
                print "xCAT service works well [Passed]"
            self.change_xcat_policy_attribute(args.nic, args.virtual_ip)
            self.deactivate_management_node(args.nic, args.virtual_ip, args.dbtype) 
            print "This machine is set to standby management node successfully..."
        except:
            raise HaException("Error: "+setup_process_msg+" [Failed]")

def parse_arguments():
    """parse input arguments"""
    parser = argparse.ArgumentParser(description="setup and configure shared data based xCAT HA MN node")
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
        obj.xcatha_setup_mn(args)
    except HaException,e:
        error_msg="=================="+e.message+"=================================="
        print error_msg        
        print "Error encountered, starting to clean up the environment"
        obj.clean_env(args.virtual_ip, args.nic, args.host_name)

if __name__ == "__main__":
    main()
