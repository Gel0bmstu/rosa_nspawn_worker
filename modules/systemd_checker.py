#!/usr/bin/env python
# -*- coding: utf-8 -*-

import subprocess
import json
import requests
import re
import os
import socket

from modules.logger import Logger
from modules.telegram_notifier import TelegramNotifier

class SystemdChecker:
    # Private variables 
    machine_name_ = ''
    username_ = ''
    user_passwd_ = ''
    current_params_ = {}
    
    commands_ = {}
    configs_ = {}

    release_ = ''
    arch_ = ''
    tg_ = {}

    # Subprocess commands
    # get_current_params_command_ = ["machinectl", "--machine="+machine_name_,"show"]
    # check_systemd_logs_command_ = ["journalctl", "-p", "3", "-xb", "-M", machine_name_]
    # login_in_container_command_ = ["machinectl", "login", machine_name_]
    # execute_command_in_container_shell_command_ = ["sudo", "machinectl", "shell", machine_name_]

    def __init__(self,
        logger,
        tg,
        configs,
        machine_name='', 
        username='',
        user_passwd='',
        release='',
        arhc=''):
        try:
            # Set settings
            self.configs_ = configs
            
            # Set logger
            self.log_ = logger

            # Set telegram notifier bot
            self.tg_ = tg

            # Apply machine name
            if machine_name:
                self.machine_name_ = machine_name
            else:
                self.machine_name_ = self.configs_['machine_name']

            self.parse_json_commands_()

            if not self.check_machine_exist(self.machine_name_):
                err = "Machine {} not founded/running, please check 'machinectl list'.".format(self.machine_name_)
                self.log_.e(err)
                self.tg_.add_error_(err)
                return

            # Apply users's settings
            # if username:
            #     self.username_ = username
            # else:
            #     self.username_ = os.environ['USER']

            # if user_passwd:
            #     self.user_passwd_ = user_passwd
            # else:
            #     self.user_passwd_ = os.environ['PASSWORD']

            # Apply os settings
            self.arch_ = arhc
            self.release_ = release
        except Exception as e:
            err = 'Unable to create SystemdChecker class: {}\n'.format(e)
            self.log_.e(err)
            self.tg_.add_error_(err)

    # Private methods
    
    # TODO: Think about how to parse commands from json with arguments
    # Mb replace query like '{{argument}}' in cycle. Look at the performance.
    def parse_json_commands_(self):
        try:
            with open("commands.json", "r") as commands_file:
                raw_commands = json.load(commands_file)

            for key, command in raw_commands.items():
                command = command.replace('{{machine_name_}}', self.machine_name_)
                self.commands_[key] = command.split()
            
            print('Commands from .json loaded successfully.')
        except Exception as e:
            err = 'Unable to parse commands.json file: \n{}'.format(e)
            print(err)
            self.tg_.add_error_(err)

    def get_current_params_(self):
        try:
            self.log_.l(u"Try to get {} system's state ...".format(self.machine_name_))

            output = subprocess.check_output(self.commands_['get_current_params'])
            output = output.decode('utf-8')

            params_lines = output.split('\n')
            # Remove last element, coz it's empty line
            params_lines.pop() 

            for line in params_lines:
                param = line.split('=')
                self.current_params_[param[0]] = param[1]
            
            self.log_.l('Getting the current system state - successfully.')
        except Exception as e:
            err = 'Unable to get current params:\n{}'.format(e)
            self.log_.e(err)
            self.tg_.add_error_(err)

    # Public methods

    # FIXME: nu eto ne smeshno daje, davai dodelay allo) 
    def login_in_container(self):
        try:
            p = subprocess.Popen(self.commands_['login_in_container_command'], \
                stdout=subprocess.PIPE, \
                stdin=subprocess.PIPE, \
                stderr=subprocess.PIPE)

            print('{}\n{}'.format(self.username_, self.user_passwd_))
            (out, err) = p.communicate(input='{}\n{}'.format(self.username_, self.user_passwd_).encode())
            # p.communicate(['machinectl', 'shell', 'touch', 'file.txt'])

        except Exception as e:
            err = 'Unable to login in container: \n{}'.format(e)
            self.log_.e(err)
            self.tg_.add_error_(err)

    def check_machine_exist(self, machine_name):
        self.log_.l('Checking machine {} for existing ...'.format(self.machine_name_))

        output = subprocess.check_output(self.commands_['check_machine_exist'])
        output = output.decode('utf-8')

        # Remove list header, like 'MACHINE CLASS SERVICE ...'
        # output = re.sub(r'\A.*\n', '', output)
        for machine in output.split('\n')[1:]:
            if machine != '' and machine.split()[0] == machine_name:
                self.log_.l('Machine {} exists.'.format(self.machine_name_))
                return True 

        return False

    def execute_command_in_container_shell(self, command, get_output=False):
        try:
            self.log_.l('Try to execute command "{}" ...'.format(command))

            if command == '':
                self.log_.e('Command should be not empty! Terminate command execution.')
                return

            if command[0] != '/':
                self.log_.w('Path to executable programm in command "{}" should be absolute.'.format(command))

            # p = subprocess.Popen(self.commands_['execute_command_in_container_shell'] + command.split(), \
            #     stdout=subprocess.PIPE, \
            #     stdin=subprocess.PIPE, \
            #     stderr=subprocess.PIPE)

            # (out, err) = p.communicate()

            out = subprocess.check_output(self.commands_['execute_command_in_container_shell'] + command.split())

            self.log_.l('Command "{}" executed successfully.'.format(command))
            self.log_.d('Command output is: {}.'.format(out.decode('utf-8')))
            # [:-1] remove '\n' symbol at the end of the 'err' string 
            # self.log_.d('Command error is: {}.'.format(err.decode('utf-8')[:-1]))

            return out.decode('utf-8')

            if get_output:
                # Out format should be 'Running as unit: run-u105.service'
                unit = err.decode('utf-8').split()[-1].split('.')[0]
                self.log_.d('Command unit is: {}'.format(unit))

                output = subprocess.check_output(self.commands_['get_output_by_unit'] + [unit])
                output = output.decode('utf-8')

                self.log_.d('Command output before split:\n{}'.format(output))

                # Log string format is:
                # -- Logs begin at Tue 2020-05-12 06:29:00 MSK, end at Thu 2020-05-14 03:11:25 MSK. --
                # мая 14 02:27:24 rosa2019.1 systemd[1]: Started /bin/ls -la /home/gel0/systemd_test.
                # мая 14 02:27:24 rosa2019.1 ls[1955]: -rw-r--r-- 1 gel0 gel0 0 May 14 02:27 /home/gel0/systemd_test
                # мая 14 02:27:24 rosa2019.1 systemd[1]: run-u105.service: Succeeded. 
                # \n (empty line)
                #
                # I remove first and last 2 lines, end delete all '*[*]: ' from log lines,
                # then added output to cmd_out
                # cmd_out = re.sub(r'--.*\n', '', output)
                cmd_out = ''

                system_log_out = output.split('\n')[:-2]
                for idx, log in enumerate(system_log_out, start=1):
                    if 'Started {}.'.format(command) in log:
                        del system_log_out[0:idx]
                        break
                    
                for idx, log in enumerate(system_log_out, start=1): 
                    if log and log != '\n': 
                        cmd_out += re.sub(r'^.*\[\d*]\:\ ', '', log)
                        if idx != len(system_log_out):
                            cmd_out += '\n'

                self.log_.d('Full command output:\n{}'.format(cmd_out))

                return cmd_out

        except Exception as e:
            err = 'Unable to execute command in container: \n{}'.format(e)
            self.log_.e(err)
            self.tg_.add_error_(err)

    def get_logs_of_service_for_last_session(self, service):
        output = subprocess.check_output(self.commands_['get_service_logs_for_last_session'] + [service])
        output = output.decode('utf-8')

        self.log_.d('Logs of the {}.service for the last session:\n{}'.format(service, output))

        return output

    def get_logs_error_of_service_for_last_session(self, service):
        output = subprocess.check_output(self.commands_['get_service_error_logs_for_last_session'] + [service])
        output = output.decode('utf-8')

        self.log_.d('Error logs of the {}.service for the last session:\n{}'.format(service, output))

        return output

    def check_logs_error_of_service_for_last_session(self, service):
        output = self.get_logs_error_of_service_for_last_session(service)

        if '-- No entries --' in output:
            self.log_.l('Error log of {}.service is empty, all is ok!'.format(service))
            return

        err = 'Error logs of the {}.service is not empty, terminated.'.format(service)
        self.log_.e(err)
        self.tg_.add_error_(err)

    def get_logs_of_service(self, service):
        output = subprocess.check_output(self.commands_['get_output_by_unit'] + [service])
        output = output.decode('utf-8')

        self.log_.d('Logs for the entire {}.service:\n{}'.format(service, output))

        return output

    def get_all_ports_used(self):
        out = self.execute_command_in_container_shell('/usr/bin/sudo /bin/netstat -tulpn', True)

        out = out.split('\n')
        for idx, line in enumerate(out, start=1): 
            if line.split()[0] == 'Proto':
                out = out[idx:]

        ports = {
            'LISTEN' : [],
            'CLOSED' : []
        }

        for port in out:
            port_fields = port.split()
            if port_fields[5] == 'LISTEN':
                ports['LISTEN'].append(re.sub(r'(.*?)\:','', port_fields[3]))
            else:
                ports['CLOSED'].append(re.sub(r'(.*?)\:','', port_fields[3]))

        return ports

    def check_if_port_is_listening(self, ip, port):
        # ports = self.get_all_ports_used()

        # if str(port) in ports['LISTEN']:
        #     self.log_.l('Port {} is open.'.format(port))
        #     return

        # self.log_.e('Port {} is closed! Terminating.'.format(port))
        # self.tg_.add_error_(err)

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # 1 sec timeout
        s.settimeout(1)
        try:
                s.connect((ip, int(port)))
                s.shutdown(socket.SHUT_RDWR)
                self.log_.l('Port {} is open.'.format(port))
                return True
        except:
            self.log_.e('Port {} is closed! Terminating.'.format(port))
            return False
        finally:
                s.close()

    def get_current_status_of_service(self, service):
        command = ' '
        command = command.join(self.commands_['get_current_service_status'] + [service])
        output = self.execute_command_in_container_shell(command, True)

        service_status = {}

        for param in output.split('\n'):
            try:
                out = param.split(': ', 1)
                service_status[out[0].replace(' ', '' )] = out[1]
            except IndexError:
                clear_param = re.sub('^\ *', '', param)
                if 'man:' in clear_param:
                    service_status['Docs'] += ', ' + clear_param
                elif clear_param:
                    service_status['Description'] = clear_param

        self.log_.d(service_status)

        if not service_status:
            err = 'An error occurred while executing a command, please, run script again'
            self.log_.e(err)
            self.tg_.add_error_(err)

        if service_status['Description']:
            if 'Unit {}.service could not be found'.format(service) in service_status['Description']:
                err = 'Service {} could not be found, please check the spelling of the entered service name.'
                self.log_.e(err)
                self.tg_.add_error_(err)

        return service_status

    def check_current_status_of_service(self, service):
        self.log_.l('Checking {}.service status ...'.format(service))

        status = self.get_current_status_of_service(service)
        if status['Active'].split()[0] != 'active':
            err = 'Service {} is not active! Terminating.'.format(service)
            self.log_.e(err)
            self.tg_.add_error_(err)
        
        self.log_.l('Service {} is active, all is ok!'.format(service))

    def check_systemd_state(self):
        try:
            self.log_.l('Checking {} machine state ...'.format(self.machine_name_))

            self.get_current_params_()

            if self.current_params_['SystemState'] == 'running':
                self.log_.l('Machine {} is running. All is ok.'.format(self.machine_name_))
                return True

            err = 'Systemd not running, current state is: {}'.format(self.current_params_['SystemState'])
            self.log_.e(err)
            self.tg_.add_error_(err)
        
            return False
        except Exception as e:
            err = 'Unable to get current systemd state:\n{}'.format(e)
            self.log_.e(err)
            self.tg_.add_error_(err)

    def check_systemd_error_logs(self):
        try:
            self.log_.l('Checking {} systemd logs'.format(self.machine_name_))

            output = subprocess.check_output(self.commands_['check_systemd_logs'])
            output = output.decode('utf-8')
            # Remove firs log line, like '-- Logs begin at ...'
            output = re.sub(r'--.*\n', '', output)

            if output == '':
                self.log_.l('Systemd error log file is clear. All is ok.')
                return True

            self.log_.e('Systemd error log file not empty.')

            if not self.configs_['logger_debug_mode']:
                self.log_.w('Turn on debug mode in configs.json file, or set -d|--debug flug, when executing the script, to see logs.')

            self.log_.d('Machine logs:\n{}'.format(output))

            return False
        except Exception as e:
            err = 'Unable to check systemd logs:\n{}'.format(e)
            self.log_.e(err)
            self.tg_.add_error_(err)
