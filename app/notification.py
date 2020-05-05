
from requests import post
# import time
# from itertools import cycle
# from alertapp import ScheduleItems, Channels, Incidents

# def send_notification(incident, notification_rule):
#     # 296246912
#     print('[*] Внутри функции send_notification')
#     # print('[*] Обращение к бд за контактами')
#     contacts = ScheduleItems.query.filter(ScheduleItems.id == notification_rule.scheduleItem_id).first().channels
#     # print('[*] Контакты и айди', contacts, incident.id)
#     body = notification_rule.body
#     print(body)
#     # time_interval = time_interval/2
#     for _, contact in enumerate(cycle(contacts.split())):
#         if Channels.query.filter(Channels.channel_source_value == contact).first() == None: 
#             continue

#         print('[*] Sending to', contact)
#         url=contact
#         type = Channels.query.filter(Channels.channel_source_value == url).first().channel_source_type
#         print(type)
#         if type=='Telegram':
#             send_message_TG(url, body)
#         time.sleep(10)
#         # time.sleep(time_interval*60)
#         incident = Incidents.query.filter(Incidents.id == incident.id).first()
#         db.session.commit()
#         print('[*] After conn to DB status is ', incident.status)
#         if incident.status!='Active':
#             print('Hurrah! You.ve done it! Incident status is ', incident.status)
#             break
        # time.sleep(time_interval*60)
        
def send_message_TG(chat_id, text):
    print('[*] We are inside TG sender')
    token = "1177389900:AAFxqBGtzNOCBPFq2QJA8FOKEWTTrQQHb_w"
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = {"chat_id": chat_id, "text": text}
    print('Before sending')
    post(url, data=data)
