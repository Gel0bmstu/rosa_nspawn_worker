#!/usr/bin/env python
# -*- coding: utf-8 -*-

import subprocess
import socket
import netifaces
import re
import ipaddress
import os
import paramiko

from modules.notifier import Notifier

class SshChecker:
    log_ = {}
    bridge_name_ = ''
    bridge_ip_ = ''
    notifier_ = {}

    def __init__(self, logger, notifier, bridge_name = 'rosa'):
        self.log_ = logger
        self.bridge_name_ = bridge_name
        self.notifier_ = notifier

    def get_bridge_ip(self):
        return self.bridge_ip_

    def get_router_addres(self):
        try: 
            self.log_.l('Try to get router ip address ...')

            gws = netifaces.gateways()
            defailt_ip = list(gws['default'].values())

            self.log_.l('Router ip address received successfully.')

            return defailt_ip[0][0]
        except Exception as e:
            err = 'Unable to get router ip address:\n{}'.format(e)
            self.log_.e(err)
            self.notifier_.add_error_(err)

    def get_local_network_addres(self):
        try:
            self.log_.l('Try to get local subnet address ...')

            router_address = self.get_router_addres()

            self.log_.l('Router ip address received successfully.')

            return re.sub(r'\.\d*[\/\d*]*$', '0/24', router_address)

        except Exception as e:
            err = 'Unable to get local subnet addres:\n{}'.format(e)
            self.log_.e(err)
            self.notifier_.add_error_(err)

    def get_free_ip_addr_in_local_network(self):
        try:
            self.log_.l('Try to get local free ip address ...')

            local_subnet_address = self.get_local_network_addres()
            self.log_.l('local subnet address {}'.format(local_subnet_address))
            addresses_list = ipaddress.ip_network(local_subnet_address)

            try:
                for addr in addresses_list.hosts():
                    a = str(addr)
                    socket.gethostbyaddr(a)
            except:
                self.log_.l('Free ip address found successfully. Address is: {}'.format(a))
                return a

            self.log_.e('There is no free ip addresses in local subnet.')
        except Exception as e:
            err = 'Unable to get free local subnet addres:\n{}'.format(e)
            self.log_.e(err)
            self.notifier_.add_error_(err)

    def get_current_ip_of_interface(self, interface):
        try:
            self.log_.l('Try to get ip of {} ...'.format(interface))

            dev = netifaces.ifaddresses(interface)

            try:
                ip = dev[2][0]['addr']
                self.log_.l('Current ip of {} is: {}'.format(interface, ip))
                return ip 
            except:
                self.log_.l("Interface doesn't have an ip address.")
        except Exception as e:
            err = 'Unable tto get ip of {}:\n{}'.format(interface, e)
            self.log_.e(err)
            self.notifier_.add_error_(err)

    def set_bridge_free_ip(self):
        try:
            self.log_.l('Try to set free ip to bridge ...')

            current_ip = self.get_current_ip_of_interface(self.bridge_name_)

            if current_ip != None:
                self.bridge_ip_ = current_ip
                self.log_.l('Bridge {} is already have an ip: {}'.format(self.bridge_name_, current_ip))
                return

            free_ip = self.get_free_ip_addr_in_local_network()

            subprocess.run(('/usr/bin/sudo ip a a {} dev {}'.format(free_ip, self.bridge_name_)).split())

            self.bridge_ip_ = free_ip

            self.log_.l('The free ip address for the bridge was set successfully.')
        except Exception as e:
            err = 'Unable to set free ip to bridge:\n{}'.format(e)
            self.log_.e(err)
            self.notifier_.add_error_(err)

    def check_if_port_is_listening(self, port = 22, ip = None):
        if ip == None and self.bridge_ip_:
            ip = self.bridge_ip_

        self.log_.l('Checking {}:{} port ...'.format(ip, port))

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # 1 sec timeout
        s.settimeout(2)
        try:
            s.connect((ip, int(port)))
            s.shutdown(socket.SHUT_RDWR)
            self.log_.l('Port {} is open.'.format(port))
            return True
        except Exception as e:
            self.log_.e('Port {} is closed! Terminating.'.format(port))
            self.log_.d('Error is: {}'.format(e))
            return False
        finally:
            s.close()

    def check_ssh_connection(self, host, user, password, password_auth_check = False):
        try:        
            self.log_.l('Checking ssh connection to {}'.format(host))

            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            if password_auth_check: 
                if user == None:
                    user = os.environ['USER']
                
                if password == None:
                    password = os.environ['PASSWD']

                    client.connect(hostname=host, username=user, password=password)
            else:
                path_to_ssh_public_key = u'/home/{}/.ssh/id_rsa.pub'.format(os.environ['USER'])
                client.connect(hostname=host, username=user, key_filename=path_to_ssh_public_key)

            self.log_.l('Сonnection with {} established successfully.'.format(host))
        except Exception as e:
            self.log_.e('Connection to {} failed!\n{}'.format(host, e))
        finally:
            client.close()
