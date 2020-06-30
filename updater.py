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
    configs = parse_json_configs('{}/rosa_nspawn_worker/config.json'.format(os.getenv('WORKSPACE')))

    # Creating logger
    logger = Logger(log_debug_mode=args.logger_debug_mode, \
        log_level=args.logger_level, \
        log_file_mode=args.logger_filelog_mode, \
        user_logfile_path=args.logger_logfile_path, \
        dir_path = configs['logger_logfile_path'], \
        configs=configs)

    subprocess.check_output(['/usr/bin/sudo', 'setenforce', '0'])
    sc = SystemdChecker(logger, configs, machine_name=args.machine_name)

    # Work with systemd container
    print(sc.execute_command_in_container_shell('/usr/bin/python3 /home/omv/updates_tracker/new_checker.py --file /home/omv/updates_tracker/package_list', True))

    subprocess.check_output(['/usr/bin/sudo', 'setenforce', '1'])
