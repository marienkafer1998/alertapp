
from requests import post
# import time
# from itertools import cycle
# from alertapp import ScheduleItems, Channels, Incidents


def send_message_TG(chat_id, text):
    print('[*] We are inside TG sender')
    token = "1177389900:AAFxqBGtzNOCBPFq2QJA8FOKEWTTrQQHb_w"
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = {"chat_id": chat_id, "text": text}
    print('Before sending')
    post(url, data=data)

def send_message_Email(email, text):
    print('[*] Immitating sendint to ', email)
    
