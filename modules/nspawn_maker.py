import os
import subprocess
import requests
import glob
import re
import time

class NspawnMaker:

    log_ = {}
    release_ = ''
    arch_ = ''
    machine_name_ = ''
    rootfs_dir_ = '/home/oleg/rosa2019.1'
    boot_dir_ =  rootfs_dir_ + '/boot'
    cache_dir_ =  rootfs_dir_ + '/var/cache/dnf'
    autologin_service_ = u'[Service] \n \
        ExecStart= \n \
        ExecStart=-/sbin/agetty --noclear --autologin rosa --keep-baud console 115200,38400,9600 $TERM'


    def __init__(self, logger, release='2019.1', arch='x86_64', machine_name='rosa2019.1', rootfs_dir=''):
        self.log_ = logger
        self.release_ = release
        self.arch_ = arch
        self.machine_name_ = machine_name

        if rootfs_dir != '':
            self.rootfs_dir_ = rootfs_dir
            self.boot_dir =  rootfs_dir + '/boot'
            self.cache_dir =  rootfs_dir + '/var/cache/dnf'

    def find_repos_(self, release, arch):
        self.log_.l('Getting rosa-repos ...')
        url = 'http://abf-downloads.rosalinux.ru/rosa{}/repository/{}/main/release/'.format(release, arch)
        resp = requests.get(url)
        if resp.status_code == 404:
            self.log_.e('bad url: {}'.format(url))
            exit(1)
        repo_file = re.search('(?<=href=")rosa-repos-.*.{}.rpm(?=")'.format(arch), resp.text)
        if len(glob.glob('rosa-repos*.rpm*')):
            subprocess.call(['/usr/bin/sudo', '/usr/bin/rm', '-rf', os.path.realpath('.') + '/*.rpm'])
        self.log_.d(subprocess.check_output(['/usr/bin/wget', url + repo_file.group(0)]))
        self.log_.l('Rosa-repos getted successfully ...')
        return repo_file.group(0)
        
    def check_machine_exist_(self, machine):
        output = subprocess.check_output(['/usr/bin/sudo', '/usr/bin/rm', '-rf', os.path.realpath('.') + '/*.rpm'])
        output = output.decode('utf-8')

        machines = s.split('\n')[1:-2]

        for machine_name in machines:
            if machine_name.split()[0] == machine:
                return True
        
        return False

    def make_container(self):
        self.log_.l('Making nspawn container ...')
        repo_pkg = self.find_repos_(self.release_, self.arch_)
        pkgs = 'NetworkManager less systemd-units openssh-server vim systemd procps-ng timezone dnf sudo usbutils passwd basesystem-minimal rosa-repos-keys rosa-repos'
        self.log_.l('Making chroot in {}'.format(self.rootfs_dir_))
        if os.path.exists(self.rootfs_dir_):
            if os.path.ismount(self.rootfs_dir_):
                self.log_.l('Directory in mounted, unmount')
                subprocess.check_output(['/usr/bin/sudo', '/bin/umount', self.cache_dir_])
                subprocess.check_output(['/usr/bin/sudo', '/bin/umount', self.boot_dir_])
                subprocess.check_output(['/usr/bin/sudo', '/bin/umount', self.rootfs_dir_])
            subprocess.check_output(['/usr/bin/sudo', 'rm', '-rf', self.rootfs_dir_])
        subprocess.check_output(['/usr/bin/sudo', 'rpm', '-Uvh', '--ignorearch', '--nodeps', repo_pkg, '--root', self.rootfs_dir_])
        subprocess.check_output(['/usr/bin/sudo', 'dnf', '-y', 'install', '--nogpgcheck', '--installroot=' + self.rootfs_dir_, \
            '--releasever=' + self.release_, '--forcearch=' + self.arch_] + pkgs.split())
        # copy fstab
        subprocess.check_output(['/usr/bin/sudo', 'cp', '-fv', 'fstab.template', self.rootfs_dir_ + '/etc/fstab'])
        # perl -e 'print crypt($ARGV[0], "password")' omv
        subprocess.check_output(['/usr/bin/sudo', 'useradd', '--prefix', self.rootfs_dir_, 'rosa', '-p', 'pabc4KTyGYBtg', '-G', 'wheel', '-m'])
        subprocess.check_output(['/usr/bin/sudo', '/usr/bin/mkdir', self.rootfs_dir_ + '/etc/systemd/system/console-getty.service.d/'])
        subprocess.check_output(['/usr/bin/sudo', '/usr/bin/touch', self.rootfs_dir_ + '/etc/systemd/system/console-getty.service.d/override.conf'])
        subprocess.check_output(['/usr/bin/sudo', 'chmod', '666', self.rootfs_dir_ + '/etc/systemd/system/console-getty.service.d/override.conf'])
        f = open(self.rootfs_dir_ + '/etc/systemd/system/console-getty.service.d/override.conf', 'w+')
        f.write(self.autologin_service_)

        if self.check_machine_exist_(self.machine_name_):
            subprocess.check_output(['/usr/bin/sudo', '/usr/bin/machinectl', 'terminate', self.machine_name_])

        devnull = open('/dev/null', "w")
        p = subprocess.Popen(['/usr/bin/sudo', 'systemd-nspawn', '-bD', self.rootfs_dir_, '-M', self.machine_name_], stdout=devnull)

        time.sleep(3)

        self.log_.l('Systemd-nspawn container created successfully')