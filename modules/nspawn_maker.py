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
    # rootfs_dir_ = self.home_dir_ + '/uptade_nspawn_container'
    boot_dir_ =  rootfs_dir_ + '/boot'
    home_dir_ = ''
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
            self.rootfs_dir_ = self.home_dir_ + '/rosa{}_{}'.format(self.release_, self.arch_)
            self.log_.l('Root directory is {}'.format(self.rootfs_dir_))

        self.boot_dir =  self.rootfs_dir_ + '/boot'
        self.cache_dir = self.rootfs_dir_ + '/var/cache/dnf'   

        self.home_dir_    = os.environ.get('HOME')
        self.abf_token_   = os.environ.get('ABF_TOKEN')
        self.root_passwd_ = os.environ.get('ROOT_PASSWORD')

        self.notifier_ = notifier

    def create_network_bridge(self, bridge_name='rosa'):
        self.log_.l('Creating network bridge {}'.format(bridge_name))
        bridge_list = subprocess.check_output(['/usr/bin/sudo', 'brctl', 'show'])
        bridges = bridge_list.decode('utf-8').split('\n')
        for b in bridges[1:]:
            line = b.split()
            self.log_.d(line)
            if len(line) > 0:
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
            auth=requests.auth.HTTPBasicAuth(self.abf_token_, ''))
        json = response.json()

        for i in range(len(json['product_build_lists'])):
            last_build_list_id = json['product_build_lists'][i]['id']

            response = requests.get('https://abf.io/api/v1/product_build_lists/{}.json'.format(last_build_list_id), \
                auth=requests.auth.HTTPBasicAuth(self.abf_token_, ''))
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

                        if os.path.exists(self.home_dir_ + '/rootfs.tar.xz'):
                            self.log_.l(self.home_dir_ + '/rootfs.tar.xz is already exixsts, removing.')
                            os.remove(self.home_dir_ + '/rootfs.tar.xz')

                        with open(self.home_dir_ + '/rootfs.tar.xz', 'wb') as f:
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
                            subprocess.check_output(['/usr/bin/sudo', 'rm', '-rf', self.rootfs_dir_])
                            self.log_.l('Old directory removed successfuly.')

                        os.mkdir(self.rootfs_dir_)
                        subprocess.check_output(['/usr/bin/sudo', 'tar', '-xvf', self.home_dir_ + '/rootfs.tar.xz', '-C', self.rootfs_dir_])
                        self.log_.l('Rootfs extracted succesfully to {}.'.format(self.rootfs_dir_))

                        if not os.path.exists(self.rootfs_dir_ + '/etc/systemd/system/console-getty.service.d'):
                            subprocess.check_output(['/usr/bin/sudo', 'mkdir', self.rootfs_dir_ + '/etc/systemd/system/console-getty.service.d'])
                        
                        subprocess.check_output(['/usr/bin/sudo', 'install', '-m', '666', '/dev/null', \
                            self.rootfs_dir_ + '/etc/systemd/system/console-getty.service.d/override.conf'])

                        with open(self.rootfs_dir_ + '/etc/systemd/system/console-getty.service.d/override.conf', 'w+') as f:
                            f.write(self.autologin_service_)

                        subprocess.check_output(['/usr/bin/sudo', 'chmod', '644', self.rootfs_dir_ + '/etc/systemd/system/console-getty.service.d/override.conf'])

                        self.log_.l('Installing utils to container ...')

                        pkgs = 'NetworkManager systemd-units openssh-server systemd procps-ng timezone dnf sudo usbutils passwd basesystem-minimal rosa-repos-keys rosa-repos git vim vim-enhanced curl'

                        subprocess.check_output(['/usr/bin/sudo', 'dnf', 'install', '-y', '--installroot', self.rootfs_dir_, '--nogpgcheck', \
                            '--releasever=' + self.release_, '--forcearch=' + self.arch_] + pkgs.split())

                        self.log_.l('Utils installed successfully')

                        subprocess.check_output(['/usr/bin/sudo', 'useradd', '--prefix', self.rootfs_dir_, 'omv', '-p', 'pabc4KTyGYBtg', '-G', 'wheel', '-m'])
                        self.log_.l('User omv added successfully.')

                        self.log_.l('Configuring sshd settings ...')

                        ps = subprocess.Popen(['/usr/bin/echo', ""], stdout=subprocess.PIPE)
                        output = subprocess.check_output(['/usr/bin/sudo', 'tee', self.rootfs_dir_ + '/etc/ssh/denyusers'], stdin=ps.stdout)
                        ps.wait()

                        subprocess.check_output(['/usr/bin/sudo', 'sed', '-i', 's/\#PermitRootLogin\ prohibit\-password/PermitRootLogin\ yes/g', \
                            self.rootfs_dir_ + '/etc/ssh/sshd_config'])
                        subprocess.check_output(['/usr/bin/sudo', 'sed', '-i', 's/\#\ *PasswordAuthentication/PasswordAuthentication/g', \
                            self.rootfs_dir_ + '/etc/ssh/ssh_config'])
                        subprocess.check_output(['/usr/bin/sudo', 'sed', '-ie', 's/\#\ *Port\ 22*/Port\ 2222/g',  self.rootfs_dir_ + '/etc/ssh/ssh_config'])
                        
                        # with open(self.rootfs_dir_ + '/etc/systemd/system/sshd.socket', 'w+') as f:
                        #     f.write('[Unit]\nDescription=SSH Socket for Per-Connection Servers\n\n[Socket]\nListenStream=2222\nAccept=yes\n\n[Install]\nWantedBy=sockets.target')

                        # with open(self.rootfs_dir_ + '/etc/systemd/system/sshd@.service', 'w+') as f:
                        #     f.write('[Unit]\nDescription=SSH Per-Connection Server for %I\n\n[Service]\nExecStart=-/usr/sbin/sshd -i\nStandardInput=socket\n\n[Install]\nWantedBy=multi-user.target\nAlias=sshd.service')

                        # The systemd sshd service will be restarted in SystemdChecker constructor
                        devnull = open('/dev/null', "w")
                        p = subprocess.Popen(['/usr/bin/sudo', 'systemd-nspawn', '-bD', self.rootfs_dir_, '-M', self.machine_name_], stdout=devnull)

                        time.sleep(3)

                        self.log_.l('Systemd-nspawn container created successfully')
                        return
                    except Exception as e:
                        err = 'Unable to create rootfs:\n{}.'.format(e)
                        self.log_.e(err)
                        self.notifier_.add_error_(err)     
                        return   
                
            self.log_.w('There is no rootfs archive in {} build. Try do downoald old versions.'.format(last_build_list_id))        
                         
