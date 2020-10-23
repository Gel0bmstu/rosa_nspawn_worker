import inspect
import os 

from datetime import datetime

# TODO: zahem dbm esli est' urovni))))
class Logger:
    log_dir_path_ = ''
    log_file_mode_ = False
    log_debug_mode_ = False
    log_file_ = ''

    log_level_ = 0

    configs_ = {}

    log_color_palette_ = {
        'DBG' : '\033[94m',
        'WRN' : '\033[35m',
        'ERR' : '\033[91m',
        'END' : '\033[0m'
    }

    def __init__(self, \
        log_file_mode, \
        log_debug_mode, \
        log_level, \
        dir_path, \
        user_logfile_path, \
        configs):

        try:
            # Set logger configs
            self.configs_ = configs

            # Set logger settings
            if log_debug_mode == None:
                self.log_debug_mode_ = self.configs_['logger_debug_mode']

            if log_level == -1:
                self.log_level_ = self.configs_['logger_level']

            if log_file_mode == None:
                self.log_file_mode = self.configs_['logger_filelog_mode']

            print('user_logfile_path:', user_logfile_path)
            if user_logfile_path:
                print('user_logfile_path not empty')
                self.log_file_mode_ = True
            else:
                self.log_file_mode_ = log_file_mode
                 
            self.log_debug_mode_ = log_debug_mode
            self.log_level_ = log_level

            if self.log_file_mode_:
                if user_logfile_path:
                    self.log_file_ = open(user_logfile_path, 'w+')
                else:    
                    if not os.path.exists(dir_path):
                        os.makedirs(dir_path)
                    
                    now = datetime.now()
                    log_file_name_ = now.strftime("/%d-%m-%Y_%H-%M-%S.log")

                    self.log_file_ = open(dir_path + log_file_name_, 'w+')

            print('\nLogger initialized successfully')
        except Exception as e:
            print('Unable to initialize logger : \n', e)
            exit()

    def get_current_time_(self):
        now = datetime.now()
        return now.strftime("%H-%M-%S")
    
    def get_caller_method_name_(self):
        curframe = inspect.currentframe()
        calframe = inspect.getouterframes(curframe, 2)
        return calframe[3][3]

    def print_(self, message, message_type):
        try:
            if self.log_level_ == 0:
                return
            elif self.log_level_ == 1 and message_type != 'ERR':
                return
            elif self.log_level_ == 2 and message_type != 'ERR' and message_type != 'WRN':
                return
            elif self.log_level_ == 3 and message_type == 'DBG':
                return

            if message_type == 'INF':
                msg = '{}: [{}] {}: {}'.format(self.get_current_time_(), message_type, self.get_caller_method_name_(), message)
                print(msg)

                if self.log_file_mode_:
                    self.log_file_.write('{}\n'.format(msg))
            elif message_type == 'DBG':
                if self.log_debug_mode_:
                    msg = '{}: {}[{}] {}: {}{}'.format(self.get_current_time_(), self.log_color_palette_[message_type], \
                        message_type, self.get_caller_method_name_(), message, self.log_color_palette_['END'])
                    non_color_msg = '{}: [{}] {}: {}\n'.format(self.get_current_time_(), message_type, self.get_caller_method_name_(), message)

                    print(msg)

                    if self.log_file_mode_:
                        self.log_file_.write(non_color_msg)
            else:
                msg = '{}: {}[{}] {}: {}{}'.format(self.get_current_time_(), self.log_color_palette_[message_type], \
                    message_type, self.get_caller_method_name_(), message, self.log_color_palette_['END'])
                non_color_msg = '{}: [{}] {}: {}\n'.format(self.get_current_time_(), message_type, self.get_caller_method_name_(), message)

                print(msg)

                if self.log_file_mode_:
                    self.log_file_.write(non_color_msg)
        except Exception as e:
            print('Unable to log messege: \n', e)
            exit()

    def e(self, message):
        self.print_(message, 'ERR')
    
    def l(self, message):
        self.print_(message, 'INF')

    def w(self, message):
        self.print_(message, 'WRN')

    def d(self, message):
        self.print_(message, 'DBG')
