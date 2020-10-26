import os
import subprocess
import requests
import glob
import re
import time

from modules.notifier import Notifier

class NspawnMaker:

    log_ = {}
    release_ = ''
    arch_ = ''
    machine_name_ = ''
    rootfs_dir_ = ''
    notifier_ = {}
    # rootfs_dir_ = '/home/oleg/uptade_nspawn_container'
    boot_dir_ =  rootfs_dir_ + '/boot'
    cache_dir_ =  rootfs_dir_ + '/var/cache/dnf'
    autologin_service_ = u'[Service] \n \
        ExecStart= \n \
        ExecStart=-/sbin/agetty --noclear --autologin root --keep-baud console 115200,38400,9600 $TERM'


    def __init__(self, logger, notifier, release='2019.1', arch='x86_64', machine_name='rosa2019.1', rootfs_dir=''):
        self.log_ = logger
        self.release_ = release
        self.arch_ = arch
        self.machine_name_ = machine_name

        if rootfs_dir != '':
            self.log_.l('Changing contaner root directory for {}'.format(rootfs_dir))
            self.rootfs_dir_ = rootfs_dir
        else:
            self.rootfs_dir_ = '/home/oleg/rosa{}_{}'.format(self.release_, self.arch_)
            self.log_.l('Root directory is {}'.format(self.rootfs_dir_))

        self.boot_dir =  self.rootfs_dir_ + '/boot'
        self.cache_dir = self.rootfs_dir_ + '/var/cache/dnf'   

        self.notifier_ = notifier

    def create_network_bridge(self, bridge_name='rosa'):
        self.log_.l('Creating network bridge {}'.format(bridge_name))
        bridge_list = subprocess.check_output(['/usr/bin/sudo', 'brctl', 'show'])
        bridges = bridge_list.decode('utf-8').split('\n')
        for b in bridges:
            line = b.split()
            if bridge_name == line[0]:
                self.log_.l('bridge {} is already exist'.format(bridge_name))
                return

        subprocess.check_output(['/usr/bin/sudo', 'brctl', 'addbr', bridge_name])
        
    def check_machine_exist(self, machine=''):
        if machine == '':
            machine = self.machine_name_

        output = subprocess.check_output(['/usr/bin/sudo', '/usr/bin/machinectl', 'list'])
        output = output.decode('utf-8')

        if 'No machines.' in output:
            self.log_.l("There is no running machines")
            return False

        machines = output.split('\n')

        self.log_.d('Machines list:')
        for machine_name in machines:
            self.log_.d('Machine name: {}'.format(machine_name))
            if machine_name != "" and machine_name.split()[0] == machine:
                self.log_.l('Machine {} exists'.format(machine))
                return True
        
        self.log_.l('Machine {} does not exist'.format(machine))
        return False

    def interrupt_machine(self, machine=''):
        if machine == '':
            machine = self.machine_name_

        subprocess.check_output(['/usr/bin/sudo', '/usr/bin/machinectl', 'terminate', machine])
        time.sleep(3)
        subprocess.check_output(['/usr/bin/sudo', 'systemctl', 'reset-failed'])

    def make_container(self):
        product_id = 0
        if self.arch_ == 'x86_64':
            product_id = 284
        elif self.arch_ == 'aarch64':
            product_id = 295
        elif self.arch_ == 'i686':
            product_id = 294

        self.log_.l('Making nspawn container ...')
        response = requests.get('https://abf.io/api/v1/products/{}/product_build_lists.json'.format(product_id), \
            auth=requests.auth.HTTPBasicAuth('S2hR6zAK7GtZ2wDniwDG', ''))
        json = response.json()
        last_build_list_id = json['product_build_lists'][0]['id']

        response = requests.get('https://abf.io/api/v1/product_build_lists/{}.json'.format(last_build_list_id), \
            auth=requests.auth.HTTPBasicAuth('S2hR6zAK7GtZ2wDniwDG', ''))
        json = response.json()
        build_results = json['product_build_list']['results']

        for result in build_results:
            if 'rootfs' in result['file_name']:
                try:
                    self.notifier_.set_rootfs_params( \
                        name=result['file_name'], \
                        date=json['product_build_list']['notified_at'], \
                        download=result['url'])

                    self.log_.l('Downloading rootfs archive ...')
                    r = requests.get(result['url'])

                    if os.path.exists('/home/oleg/rootfs.tar.xz'):
                        self.log_.l('/home/oleg/rootfs.tar.xz is already exixsts, removing.')
                        os.remove('/home/oleg/rootfs.tar.xz')

                    with open('/home/oleg/rootfs.tar.xz', 'wb') as f:
                        f.write(r.content)

                    self.log_.l('Rootfs downloaded successfully, unpacking to {} ...'\
                        .format(self.rootfs_dir_))

                    if os.path.exists(self.rootfs_dir_):
                        self.log_.l('Directory {} is already exists, removing ...'.format(self.rootfs_dir_))
                        if os.path.ismount(self.rootfs_dir_):
                            self.log_.l('Directory is mounted, unmount ...')
                            subprocess.check_output(['/usr/bin/sudo', '/bin/umount', self.cache_dir_])
                            subprocess.check_output(['/usr/bin/sudo', '/bin/umount', self.boot_dir_])
                            subprocess.check_output(['/usr/bin/sudo', '/bin/umount', self.rootfs_dir_])
                            self.log_.l('Directory unmounted successfully.')
                        self.log_.l('Removing {} dir'.format(self.rootfs_dir_))
                        subprocess.check_output(['/usr/bin/sudo', 'rm', '-rf', self.rootfs_dir_])
                        self.log_.l('Old directory removed successfuly.')

                    os.mkdir(self.rootfs_dir_)
                    subprocess.check_output(['/usr/bin/sudo', 'tar', '-xvf', '/home/oleg/rootfs.tar.xz', '-C', self.rootfs_dir_])
                    self.log_.l('Rootfs extracted succesfully to {}.'.format(self.rootfs_dir_))

                    if not os.path.exists(self.rootfs_dir_ + '/etc/systemd/system/console-getty.service.d'):
                        subprocess.check_output(['/usr/bin/sudo', 'mkdir', self.rootfs_dir_ + '/etc/systemd/system/console-getty.service.d'])
                    
                    subprocess.check_output(['/usr/bin/sudo', 'install', '-m', '666', '/dev/null', \
                        self.rootfs_dir_ + '/etc/systemd/system/console-getty.service.d/override.conf'])

                    f = open(self.rootfs_dir_ + '/etc/systemd/system/console-getty.service.d/override.conf', 'w+')
                    f.write(self.autologin_service_)

                    subprocess.check_output(['/usr/bin/sudo', 'chmod', '644', self.rootfs_dir_ + '/etc/systemd/system/console-getty.service.d/override.conf'])

                    self.create_network_bridge('rosa')

                    devnull = open('/dev/null', "w")
                    p = subprocess.Popen(['/usr/bin/sudo', 'systemd-nspawn', '-bD', self.rootfs_dir_, '-M', self.machine_name_, '--network-bridge', 'rosa'], stdout=devnull)

                    time.sleep(3)

                    self.log_.l('Systemd-nspawn container created successfully')
                    return
                except Exception as e:
                    err = 'Unable to create rootfs:\n{}.'.format(e)
                    self.log_.e(err)
                    self.notifier_.add_error_(err)     
                    return            
            
        err = 'Unable to get rootfs archive form abf:\nNo archive in last buildlist.'
        self.log_.e(err)
        self.notifier_.add_error_(err)
