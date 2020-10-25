import requests
import os

class TelegramNotifier:
    api_token_ = '1150474330:AAEWH1nSIoYTYJmF14AxlIkcoyFgSn2gxl4'
    chats_id_ = ['-483928837']
    error_stack_ = []
    error_conter_ = 1

    rootfs_filename_ = ''
    rootfs_build_date_ = ''
    rootfs_download_link_ = ''

    def __init__(self):
        pass
    
    def send_message(self, message):
        for chat in self.chats_id_:
            response = requests.post(url='https://api.telegram.org/bot{}/sendMessage'.format(self.api_token_),
                data = {
                    "chat_id": chat,
                    "text": message,
                }
            )
    
    def add_error_(self, err):
        self.error_stack_.append('{}: {}'.format(self.error_conter_, err))
        self.error_conter_ = self.error_conter_ + 1

    def get_error_stack_size_(self):
        return len(self.error_stack_)

    def set_rootfs_params(self, name, date, download):
        self.rootfs_build_date_ = date
        self.rootfs_filename_ = name
        self.rootfs_download_link_ = download

    def alert(self):
        if self.get_error_stack_size_() > 0:
            alert_message = ['There is some errors:\n\n{errors}\n\n'
            'Rootfs archive name: {rootfs_name}\n',
            'Rootfs build date:   {rootfs_build_date}\n'
            'Rootfs archive link: {rootfs_download_link}\n\n'
            'Build log: {build_log_link}\n']

            link = '{url}job/{name}/{id}/console'.format(url=os.getenv('JENKINS_URL'), name=os.getenv('JOB_BASE_NAME'), id=os.getenv('BUILD_ID'))

            for chat in self.chats_id_:
                response = requests.post(url='https://api.telegram.org/bot{}/sendMessage'.format(self.api_token_),
                    data = {
                        "chat_id": chat,
                        "text": ''.join(alert_message).format( \
                            errors='\n\n'.join(self.error_stack_), 
                            rootfs_name=self.rootfs_filename_,
                            rootfs_build_date=self.rootfs_build_date_,
                            rootfs_download_link=self.rootfs_download_link_,
                            build_log_link=link)
                        # "parse_mode": "MarkdownV2"
                    }
                )
