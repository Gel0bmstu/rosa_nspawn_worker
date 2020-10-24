import requests
import os

class TelegramNotifier:
    api_token_ = '1150474330:AAEWH1nSIoYTYJmF14AxlIkcoyFgSn2gxl4'
    chats_id_ = ['-483928837']

    def __init__(self):
        pass
    
    def send_message(self, message):
        for chat in self.chats_id_:
            print(message, chat)
            response = requests.post(url='https://api.telegram.org/bot{}/sendMessage'.format(self.api_token_),
                data = {
                    "chat_id": chat,
                    "text": message,
                }
            )
    
    def alert(self, error):
        alert_message = 'There is some errors:\n\n{}\n\nBuild log: {}'
        link = '{url}job/{name}/{id}/console'.format(url=os.getenv('JENKINS_URL'), name=os.getenv('JOB_BASE_NAME'), id=os.getenv('BUILD_ID'))

        for chat in self.chats_id_:
            print(message, chat)
            response = requests.post(url='https://api.telegram.org/bot{}/sendMessage'.format(self.api_token_),
                data = {
                    "chat_id": chat,
                    "text": alert_message.format(error, link),
                }
            )
