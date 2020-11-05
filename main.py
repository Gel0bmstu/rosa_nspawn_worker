#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import json
import subprocess

from modules.systemd_checker import SystemdChecker
from modules.logger import Logger
from modules.ssh_checker import SshChecker
from modules.nspawn_maker import NspawnMaker
from modules.notifier import Notifier

def parse_script_arguments():
    parser = argparse.ArgumentParser(description='Script to work with systemd-nspawn container.')
    parser.add_argument('-d', '--debug', dest='logger_debug_mode', action='store_true',
                        default=None, help='enable logger debug mode')
    parser.add_argument('-f', '--log-file', dest='logger_filelog_mode', action='store_true',
                        default=None, help='enable logging to file mode')
    parser.add_argument('-fp', '--log-file-path', dest='logger_logfile_path', action='store',
                        default='', help='set logfile path and enable logger "file_log_mode"')
    parser.add_argument('-p', '--priority', dest='logger_level', action='store', type=int, default=-1,
                        help='filter output by priority ranges: 0 - no logs, 1 - errors only,\
                            2 - errors and warnings, 3 - errors, warnings and info, 4 - precursor and debug.')
    parser.add_argument('-m', '--machine', action='store', default='', dest='machine_name', help='set systemd machine name')
    parser.add_argument('-r', '--root-dir', action='store', default='', dest='root_dir', help='set systemd container root directory')
    
    # Control params

    # Set rootfs arch
    parser.add_argument('-a', '--arch', action='store', default='x86_64', dest='arch', help='set systemd container rootfs arch')

    # Cehck state of nspawn container
    parser.add_argument('-c', '--check-state', action='store_true', dest='check_state', help='check sysstemd-container state')

    # Cehck status of service
    parser.add_argument('-s', '--service', action='store', default=None, dest='service_name', help='check state of setted service in container')


    return parser.parse_args()

def parse_json_configs(path_to_config = "config.json"):
    try:
        configs = {}

        with open(path_to_config, "r") as configs_file:
            raw_config = json.load(configs_file)

        for key, config in raw_config.items():
            configs[key] = config
        
        print('Settings from config.json loaded successfully.')

        return configs
    except Exception as e:
        print('Unable to parse configs.json file: \n', e)
        exit() 

if __name__ == '__main__':
    try:
        # Parsing script arguments and config file
        args = parse_script_arguments()
        configs = parse_json_configs()

        # Creating logger
        logger = Logger(log_debug_mode=args.logger_debug_mode, \
            log_level=args.logger_level, \
            log_file_mode=args.logger_filelog_mode, \
            user_logfile_path=args.logger_logfile_path, \
            dir_path = configs['logger_logfile_path'], \
            configs=configs)

        notifier = Notifier()

        subprocess.check_output(['/usr/bin/sudo', 'setenforce', '0'])
        
        nm = NspawnMaker(logger, notifier, release='2019.1', arch=args.arch, rootfs_dir=args.root_dir)
        nm.make_container()

        # Work with systemd container
        sc = SystemdChecker(logger, notifier, configs, machine_name=args.machine_name)
        if args.check_state:
            sc.check_systemd_state()
            sc.check_systemd_error_logs()
        
        if args.service_name != None:
            sc.check_current_status_of_service(args.service_name)
            sc.check_logs_error_of_service_for_last_session(args.service_name)

        # Work with container network
        pc = SshChecker(logger = logger, notifier = notifier, use_bridge = False)
        # pc.set_bridge_free_ip()
        pc.check_if_port_is_listening(port = 2222)

        nm.interrupt_machine()

        subprocess.check_output(['/usr/bin/sudo', 'setenforce', '1'])

        if notifier.get_error_stack_size_() > 0:
            # notifier.alert()
            exit(-1)
    except Exception as e:
        # notifier.alert()
        exit(-1)
