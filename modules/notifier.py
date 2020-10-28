import requests
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib

class TelegramNotifier:
    api_token_ = ''
    chats_id_ = []

    def __init__(self):
        self.api_token_ = os.environ.get('NOTIFIER_BOT_API_TOKEN')
        self.chats_id_.append(os.environ.get('TELEGRAM_NOTIFICATION_CHAT_ID'))

    def alert(self, text):
        for chat in self.chats_id_:
            response = requests.post(url='https://api.telegram.org/bot{}/sendMessage'.format(self.api_token_),
                data = {
                    "chat_id": chat,
                    "text": text
                    # "parse_mode": "MarkdownV2"
                }
            )

class EmailNotifier:
    adress_ = ''
    pass_ = ''
    receivers_list_ = []
    
    def __init__(self):
        self.adress_ = os.environ.get('NOTIFIER_EMAIL_ADRESS')
        self.pass_   = os.environ.get('NOTIFIER_EMAIL_PASS')

    def alert(self, text):        
        server = smtplib.SMTP('smtp.gmail.com: 587')
        server.starttls()
        server.login(self.adress_, self.pass_)
        
        msg = MIMEMultipart()
        msg['From']    = self.adress_
        msg['Subject'] = 'Error report'
        msg.attach(MIMEText(text, 'plain'))

        r = requests.get('http://35.228.159.44:3000/')
        self.receivers_list_ = r.content.decode('utf-8').split('\n')

        for receiver in self.receivers_list_:
            if receiver != '':
                msg['To'] = receiver
                server.sendmail(msg['From'], msg['To'], msg.as_string())
        
        server.quit()

class Notifier:
    error_stack_ = []
    error_conter_ = 1

    rootfs_filename_ = ''
    rootfs_build_date_ = ''
    rootfs_download_link_ = ''

    tg_ = {}
    email_ = {}

    def __init__(self):
        self.tg_ = TelegramNotifier()
        self.email_ = EmailNotifier()

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
        alert_message = ['There is some errors:\n\n{errors}\n\n'
            'Rootfs archive name: {rootfs_name}\n',
            'Rootfs build date:   {rootfs_build_date}\n'
            'Rootfs archive link: {rootfs_download_link}\n\n'
            'Build log: {build_log_link}\n']

        link = '{url}job/{name}/{id}/console'.format(url=os.getenv('JENKINS_URL'), name=os.getenv('JOB_BASE_NAME'), id=os.getenv('BUILD_ID'))

        text = ''.join(alert_message).format( \
                        errors='\n\n'.join(self.error_stack_), 
                        rootfs_name=self.rootfs_filename_,
                        rootfs_build_date=self.rootfs_build_date_,
                        rootfs_download_link=self.rootfs_download_link_,
                        build_log_link=link)

        self.alert_tg(text)
        self.alert_mail(text)

    def alert_tg(self, text):
        self.tg_.alert(text)

    def alert_mail(self, text):
        self.email_.alert(text)