#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import json
import subprocess
import os

from modules.systemd_checker import SystemdChecker
from modules.logger import Logger
from modules.ssh_checker import SshChecker
from modules.nspawn_maker import NspawnMaker

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
    parser.add_argument('-r', '--root-dir', action='store', default=None, dest='root_dir', help='set systemd container root directory')

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

    subprocess.check_output(['/usr/bin/sudo', 'setenforce', '0'])
    sc = SystemdChecker(logger, configs, machine_name='updater')
    # nm = NspawnMaker(logger=logger, release='2019.1', arch='x86_64', machine_name='updater', rootfs_dir='/home/oleg/update_nspawn_container')
    # nm.make_container()
    
    # Work with systemd container
    # print(sc.execute_command_in_container_shell('/usr/bin/git clone https://github.com/Gel0bmstu/updates_tracker /home/omv/updates_tracker', True))
    print(sc.execute_command_in_container_shell('/usr/bin/python3 /home/omv/updates_tracker/new_checker.py --package vim', True))
    # print(sc.execute_command_in_container_shell('/bin/echo "da"', True))


    subprocess.check_output(['/usr/bin/sudo', 'setenforce', '1'])
