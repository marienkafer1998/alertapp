#docker-compose up -d --build app
# celery -A alertapp.celery worker --loglevel=info

from flask import Flask, request, jsonify, render_template, flash, redirect, url_for
from flask_moment import Moment
from celery import Celery
from flask_sqlalchemy import SQLAlchemy
from collections import defaultdict
from datetime import datetime, timedelta
from flask_login import login_user, login_required, logout_user, UserMixin, LoginManager, current_user
from forms import TypeForm
import time, asyncio
from sqlalchemy import distinct, select
from itertools import cycle
import json

from notification import send_message_TG
# from models import Alerts

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql+psycopg2://alertapp:alertapp@localhost/alertapp'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = False

app.config['CELERY_BROKER_URL'] = 'redis://127.0.0.1:6379/0'
app.config['CELERY_RESULT_BACKEND'] = 'redis://127.0.0.1:6379/0'
app.config['CELERY_RESULT_SERIALIZER']= 'json'

celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'], include=['alertapp'])
celery.conf.update(app.config)

moment = Moment(app)
app.config.from_object('config')
db = SQLAlchemy(app)
manager = LoginManager(app)



class Alerts(db.Model):

    __tablename__ = 'Alerts'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    service = db.Column(db.String(64), unique=False, nullable=False)
    severity = db.Column(db.String(64), nullable=False)
    incident_id =  db.Column(db.Integer, db.ForeignKey('Incidents.id'), nullable=False)


class TypeOfIncident(db.Model):

    __tablename__ = 'TypeOfIncident'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    typeName = db.Column(db.String(30), unique=True, nullable=False)
    description = db.Column(db.String(300), nullable=False)
    labels = db.Column(db.Text, unique=True, nullable=False) #instead of JSON and ARRAY
    active = db.Column(db.Boolean, nullable=False)
    interval = db.Column(db.Integer, nullable=False)
    incidents = db.relationship('Incidents', backref='TypeOfIncident', lazy=True)
    schedule_items = db.relationship('ScheduleItems', backref='TypeOfIncident', lazy=True, cascade = "all, delete, delete-orphan")


class Incidents(db.Model):

    __tablename__ = 'Incidents'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    type_id =  db.Column(db.Integer, db.ForeignKey('TypeOfIncident.id'), nullable=False)
    start = db.Column(db.DateTime, nullable=True)
    end = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(30), nullable=False)
    postponed_to = db.Column(db.DateTime, nullable=True)
    user_id =  db.Column(db.Integer, db.ForeignKey('Users.id'), nullable=True)
    alerts = db.relationship('Alerts', backref='Incidents', lazy=True, cascade = "all, delete, delete-orphan")


users = db.Table('users',
    db.Column('ScheduleItem_id', db.Integer, db.ForeignKey('ScheduleItems.id')),
    db.Column('User_id', db.Integer, db.ForeignKey('Users.id')),
    db.Column('Position', db.Integer, autoincrement=True))

class ScheduleItems(db.Model):

    __tablename__ = 'ScheduleItems'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    type_id =  db.Column(db.Integer, db.ForeignKey('TypeOfIncident.id'), nullable=False)
    dayOfWeek = db.Column(db.Integer)
    users = db.relationship('Users', secondary=users,
        backref=db.backref('ScheduleItems'))


class Channels(db.Model):

    __tablename__ = 'Channels'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id =  db.Column(db.Integer, db.ForeignKey('Users.id'), nullable=False)
    channel_source_type = db.Column(db.String(60), nullable=False) # probably should be in another table
    channel_source_value = db.Column(db.String(150), nullable=False)

class NotificationRules(db.Model):

    __tablename__ = 'NotificationRules'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    incident_id =  db.Column(db.Integer, db.ForeignKey('Incidents.id'), nullable=False)
    scheduleItem_id = db.Column(db.Integer, db.ForeignKey('ScheduleItems.id'), nullable=False)
    body = db.Column(db.Text, nullable=False) #text-message for messages
    interval = db.Column(db.Integer, nullable=False)
    status = db.Column(db.Boolean, nullable=False)


class Users(db.Model, UserMixin):

    __tablename__ = 'Users'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(20), nullable=False)
    password = db.Column(db.String(20), nullable=False)
    fullName = db.Column(db.String(60), nullable=False)
    incidents = db.relationship('Incidents', backref='Users', lazy=True)
    channels = db.relationship('Channels', backref='Users', lazy=True, cascade = "all, delete, delete-orphan")


@manager.user_loader
def load_user(user_id):
    return Users.query.get(user_id)

@app.route('/login', methods=['GET', 'POST'])
def login_page():
    if request.method=='POST':
        login = request.form.get('user')
        password = request.form.get('password')
        if login and password:
            user = Users.query.filter_by(username=login).first()
            if user and user.password==password:
                login_user(user)
                return redirect(url_for('main_page'))
            else:
                flash('Login or password is not correct')
        else:
            flash('Please fill login and password fields')
        return render_template('login.html')
    return render_template('login.html')

@app.route('/logout', methods=['GET', 'POST'])
# @login_required
def logout():
    logout_user()
    return redirect(url_for('login_page'))


@celery.task(serializer='json')
def postponed_incident(id):
    incident=Incidents.query.get(id)
    print(incident.status)
    # incident.postponed_to <= datetime.now() and 
    if (incident.status == 'Postponed'):
        print('inside cicle')
        incident.status = 'Active'
        incident.postponed_to = None
        send_notification.delay(incident.id) 
        db.session.commit()
    return json.dumps({"status": True})



@celery.task(serializer='json')
def send_notification(id):
    print('[*] Внутри функции send_notification')
    incident = Incidents.query.get(id)
    notification_rule=NotificationRules.query.filter(NotificationRules.incident_id==id).first()
    users = ScheduleItems.query.filter(ScheduleItems.id == notification_rule.scheduleItem_id).first().users
    contacts=[]
    for user in users:
        for channel in user.channels:
            contacts.append(channel)
    print(contacts)
    body = notification_rule.body
    time_interval=TypeOfIncident.query.get(incident.type_id).interval/2 
    print(body)
    for _, contact in enumerate(cycle(contacts)):
        url=contact.channel_source_value 
        type = contact.channel_source_type
        print(type)
        if type=='Telegram':
            send_message_TG(url, body)
        if type=='Email':
            print('Sending to email')
        time.sleep(10)
        # time.sleep(time_interval*60)
        incident = Incidents.query.filter(Incidents.id == incident.id).first()
        db.session.commit()
        if incident.status!='Active':
            print('Hurrah! You.ve done it! Incident status is ', incident.status)
            return json.dumps({"status": True})
            break
        time.sleep(10)
        # time.sleep(time_interval*60)
    return json.dumps({"status": True})


# разбить на функцию формирования инцидентов
@app.route('/receive', methods=['POST', 'GET'])
def get_data():
    if request.method == 'POST':
        data = request.get_json()
        types_incidents = db.session.query(TypeOfIncident.id, TypeOfIncident.labels).filter(TypeOfIncident.active == True).all()
        num_alert = len(data)
        incidents = defaultdict(list)
        for alert in data:
            labels = alert['labels'].values()
            for type_ in types_incidents:
                correct_type = True
                for label in type_[1].split():
                    if label not in labels:
                        correct_type = False
                        break
                if correct_type:
                    incidents[type_[0]].append(alert)
        for incident in incidents.items():
            create_incident(incident)
            
        return jsonify(data)
    return "no item"


def create_incident(incident):
    print('[*] Создание инцидента')
    incident_obj = Incidents(type_id = incident[0], start = datetime.now(), status = 'Active')
    print('[*] Добавляю инцидент')
    db.session.add(incident_obj)
    print('[*] Делаю коммит')
    db.session.commit()
    for alert in incident[1]:
        labels = alert['labels']
        print('[*] Создаю алерт')
        alert_obj = Alerts(severity=labels['severity'], service=labels['service'], Incidents=incident_obj)
        print('[*] Добавлю алерт')
        db.session.add(alert_obj)
        print('[*] Коммит')
        db.session.commit()
    # Создание NotificationRule для этого входящего инцидента
    day = datetime.today().isoweekday()
    sch = ScheduleItems.query.filter(ScheduleItems.dayOfWeek == day, ScheduleItems.type_id == incident_obj.type_id).first()
    print('[*] ScheduleItems id, day, type id', sch.id, day, incident_obj.type_id)
    url_inc = 'http://localhost:1080/incidents/'+str(incident_obj.id)
    message = 'Hello, big fat popa! You have '+incident_obj.TypeOfIncident.typeName+' incidents! But you dont need to care about it, because its test one!'

    # message = 'Hurry! You have '+incident_obj.TypeOfIncident.typeName+' incidents! Check it here '+url_inc
    notification = NotificationRules(incident_id = incident_obj.id, scheduleItem_id = sch.id, body = message, interval = 1, status = True)
    db.session.add(notification)
    db.session.commit()
    send_notification.delay(incident_obj.id)


@app.route('/', methods=['GET'])
@app.route('/incidents', methods=['GET'])
def main_page():
    incidents=Incidents.query.all()
    return render_template('incidents.html', incidents=incidents)


@app.route('/incidents/<string:filter>', methods=['GET', 'POST'])
# @login_required
def show_incidents(filter):
    incidents=Incidents.query.all()
    return render_template('incidents.html', incidents=incidents, filter=filter)

@app.route('/incidents/<int:id>', methods=['GET', 'POST'])
# @login_required
def show_incident(id):
    incident = Incidents.query.get(id)
    print('[*] Внутри конкретного инцидента')
   
    option_list=['Active', 'Work-in-progress', 'Postponed', 'Complete']
    actual_status = incident.status
    option_list.remove(actual_status)
    option_list.append(actual_status)
    if request.method == 'POST':
        print('[*] Changing incidents with id = ', incident.id)
        print('[*] status before', incident.status)
        status = request.form.get('option')
        option_list.remove(status)
        option_list.append(status)
        incident.status=status
        if status=='Complete':
            end = datetime.now()
            print('[*] Добавляю время')  
            notification = NotificationRules.query.filter(NotificationRules.incident_id == incident.id).first()
            db.session.delete(notification)
            db.session.commit()
            incident.end = end
        if (status=='Postponed' and incident.postponed_to == None):
            print('[*] Добавляю отложенное время') 
            postponed_time = int(request.form.get('time'))
            postponed_to = timedelta(days = postponed_time)
            incident.postponed_to = incident.start + postponed_to
            # postponed_incident.apply_async(args=[id], countdown=60*60*24*postponed_time)
            postponed_incident.apply_async(args=[id], countdown=60*postponed_time)
            
        else:
            incident.postponed_to = None
        if incident.user_id == None:
            print('[*] Добавляю юзера')
            incident.user_id= current_user.id
        
        print('[*] status after', incident.status)
        print('[*] Делаю коммит ', incident.status)
        db.session.commit()  


        return render_template('incident.html', incident=incident, option_list=[])
    return render_template('incident.html', incident=incident, option_list=option_list)


@app.route('/types_incidents', methods=['GET'])
# @login_required
def show_types():
    print('[*] Show types')
    on_types = TypeOfIncident.query.filter(TypeOfIncident.active == True).all()
    off_types = TypeOfIncident.query.filter(TypeOfIncident.active == False).all()
    return render_template('types.html', active=on_types, nonactive=off_types)

@app.route('/types_incidents/create', methods=['POST','GET'])
def create_type():
    if request.method == 'POST':
        name = request.form['typeName']
        description = request.form['description']
        labels = request.form['labels']
        active = request.form['active']
        interval = request.form['interval']
        print(active)
        if active=='y':
            active=True
        else:
            active=False
        
        type = TypeOfIncident(typeName=name, description=description, labels=labels, active=active, interval=interval)
        db.session.add(type)
        db.session.commit()
        default = Users.query.filter(Users.username=='admin').first()
        users=[default]
        #create DefaultChannels like table with position thing
        # for default in db.session.query(defaultChannels).all():
        #     channel = Channels.query.get(default.Channel_id)
        #     chan.append(channel)
        for day in range(1,8):
            schItem_obj = ScheduleItems(TypeOfIncident = type, dayOfWeek=day, users = users)
            print('[*] ScheduleItems for', day, schItem_obj.users)
            db.session.add(schItem_obj)
               
            db.session.commit()
        return redirect(url_for('show_types'))
    form = TypeForm()
    return render_template('create_type.html', form=form)

@app.route('/types_incidents/<id>/edit', methods=['POST', 'GET'])
def edit_type(id):
    type = TypeOfIncident.query.get(id)
    if request.method == 'POST':
        form = TypeForm(formdata=request.form, obj=type)
        form.populate_obj(type)
        
        db.session.commit()
        return redirect(url_for('show_types'))
    form = TypeForm(obj=type)
    return render_template('edit_type.html', type=type, form=form)


@app.route('/notification/<int:id>', methods=['POST'])
def delete_defchan(id):
    print('[*] Deleting default channel', id)
    delete = defaultChannels.delete().where(defaultChannels.c.Channel_id==id)
    db.engine.execute(delete)

    return redirect(url_for('notification_settings'))

@app.route('/schedule', methods=['GET'])
# @login_required
def show_schedule():
    on_types = TypeOfIncident.query.filter(TypeOfIncident.active == True).all()
    off_types = TypeOfIncident.query.filter(TypeOfIncident.active == False).all()
    return render_template('schedule.html', active=on_types, nonactive=off_types)

@app.route('/schedule/order', methods=['POST'])
# @login_required
def order():
    if request.method == 'POST':
        order = request.get_json()
        print('[*] ORDER ',order)
        item_id = int(order.pop(-1))
        ScheduleItem = ScheduleItems.query.get(item_id)
        for position in range(1, len(order)+1):
            
            user_id = int(order[position-1])
            print(position, user_id)
            stmt = users.update().\
            where(users.c.ScheduleItem_id==item_id).where( users.c.User_id==user_id).values(Position=int(position))
            print(stmt)
            db.engine.execute(stmt)


        print(type(order[0]))
        print(order)


@app.route('/schedule/<id>/editing', methods=['GET', 'POST'])
# @login_required
def edit_scheduleItem(id):
    users_list = db.session.query(users.c.User_id).filter(users.c.ScheduleItem_id==id).all()
    user_chain=[]
    for _id in users_list:
        user_chain.append(Users.query.get(_id[0]))
    option_users=[obj[0] for obj in db.session.query(distinct(Users.fullName)).all()] 
    week = {1: 'Monday', 2: 'Tuesday', 3: 'Wednesday', 4: 'Thursday', 5: 'Friday', 6: 'Saturday', 7: 'Sunday', }
    scheduleItem = ScheduleItems.query.get(id)
    # print(scheduleItem.channels)        
    return render_template('edit_scheduleItem.html', scheduleItem = scheduleItem, day = week[scheduleItem.dayOfWeek], option_users=option_users, users=user_chain)

@app.route('/schedule/<id_item>/add', methods=['POST'])
# @login_required
def add_user_to_chain(id_item):
    scheduleItem = ScheduleItems.query.get(id_item)
    print('[*] Добавляем нового юзера в конкретную цепочку')
    user = request.form.get('option_user')
    user = Users.query.filter(Users.fullName==user).first()
    scheduleItem.users.append(user)         
    db.session.commit()
    return redirect(url_for('edit_scheduleItem', id=id_item))


@app.route('/schedule/<id_item>/delete/<id_user>', methods=['POST'])
# @login_required
def delete_user_from_chain(id_item, id_user):
    print('Удаляем канал из ScheduleItem c id= ', id_item)
    scheduleItem = ScheduleItems.query.filter(ScheduleItems.id == id_item).first()
    user=Users.query.get(id_user)
    scheduleItem.users.remove(user)  
    db.session.commit()
    return redirect(url_for('edit_scheduleItem', id=id_item))


@app.route('/test', methods=['GET'])
def test():
    
    default = db.session.query(defaultChannels).all()
    print(default)
    return "hi"

@app.route('/profile', methods=['GET'])
def profile():
    id = 1 
    # user = Users.query.get(current_user.id)
    user = Users.query.get(id)
    incidents = Incidents.query.filter(Incidents.user_id == user.id).all()
    all = db.session.query(Incidents).count()

    return render_template('profile.html', user = user, incidents=incidents, all=all)

@app.route('/profile/<string:query>', methods=['GET','POST'])
def profile_info(query):
    qur=query
    print(query, qur)
    id = 1 
    # user = Users.query.get(current_user.id)
    user = Users.query.get(id)

    incidents = Incidents.query.filter(Incidents.user_id == user.id).all()
    all = db.session.query(Incidents).count()
    
    if request.method == 'POST' and query=='channels': # изменение каналов
        type = request.form.get('type')
        value = request.form.get('value')
        channel = Channels(user_id=user.id, channel_source_type=type, channel_source_value=value)
        db.session.add(channel)
        db.session.commit()
        query=''
        return redirect(url_for('profile'))
    if query:
        return render_template('user_inc.html', query = query, incidents = incidents)
    return render_template('profile.html', user = user, query = query, incidents = incidents, all=all)

@app.route('/profile/channels/<id>/deleting', methods=['GET', 'POST'])
def delete_user_channel(id):
    print(request.method)
    if request.method == 'POST':
        channel = Channels.query.get(id)
        db.session.delete(channel)
        db.session.commit()
    return redirect(url_for('profile'))


@app.after_request
def redirect_to_signin(response):
    if response.status_code == 401:
        return redirect(url_for('login_page') + '?next=' + request.url)
    return response




if __name__ == '__main__':

    db.create_all()
    # queue = Incidents.query.filter(Incidents.status=='Postponed')
    app.run(host='0.0.0.0', port=1080, debug=True)