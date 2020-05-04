#docker-compose up -d --build app

from flask import Flask, request, jsonify, render_template, flash, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from collections import defaultdict
from datetime import datetime
from flask_login import login_user, login_required, logout_user, UserMixin,LoginManager, current_user
from forms import TypeForm
import time
from itertools import cycle
# from models import Alerts, Incidents, TypeOfIncident, Users

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql+psycopg2://alertapp:alertapp@localhost/alertapp'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = False
app.config.from_object('config')
db = SQLAlchemy(app)
manager = LoginManager(app)

contact_list = 'ex@gmail.com ex2@gmail.com'


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
    description = db.Column(db.String(300), unique=True, nullable=False)
    labels = db.Column(db.Text, nullable=False) #instead of JSON and ARRAY
    active = db.Column(db.Boolean, nullable=False)
    incidents = db.relationship('Incidents', backref='TypeOfIncident', lazy=True)
    schedule_items = db.relationship('ScheduleItems', backref='TypeOfIncident', lazy=True)


class Incidents(db.Model):

    __tablename__ = 'Incidents'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    type_id =  db.Column(db.Integer, db.ForeignKey('TypeOfIncident.id'), nullable=False)
    start = db.Column(db.DateTime, nullable=True)
    end = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(30), nullable=False)
    user_id =  db.Column(db.Integer, db.ForeignKey('Users.id'), nullable=True)
    alerts = db.relationship('Alerts', backref='Incidents', lazy=True)

class ScheduleItems(db.Model):

    __tablename__ = 'ScheduleItems'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    type_id =  db.Column(db.Integer, db.ForeignKey('TypeOfIncident.id'), nullable=False)
    dayOfWeek = db.Column(db.Integer) # probably doesn't work
    channels = db.Column(db.Text, nullable=False)

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
    username = db.Column(db.String(60), nullable=False)
    fullName = db.Column(db.String(60), nullable=False)
    password = db.Column(db.String(260), nullable=False)
    incidents = db.relationship('Incidents', backref='Users', lazy=True)
    channels = db.relationship('Channels', backref='Users', lazy=True)


@manager.user_loader
def load_user(user_id):
    return Users.query.get(user_id)

@app.route('/login', methods=['GET', 'POST'])
def login_page():
    login = request.form.get('login')
    password = request.form.get('password')
    print(login, password)
    if login and password:
        user = Users.query.filter_by(username=login).first()
        print(user)
        if user and user.password==password:
            print('we are here')
            login_user(user)
            return redirect(url_for('show_incidents'))
        else:
            flash('Login or password is not correct')
    else:
        flash('Please fill login and password fields')
    return render_template('login.html')

@app.route('/logout', methods=['GET', 'POST'])
# @login_required
def logout():
    logout_user()
    return redirect(url_for('login_page'))




@app.route('/receive', methods=['POST', 'GET'])
def get_data():
    if request.method == 'POST':
        data = request.get_json()
        num_types = db.session.query(TypeOfIncident).count()
        num_alert = len(data)
        types_incidents = db.session.query(TypeOfIncident.id, TypeOfIncident.labels).filter(TypeOfIncident.active == True).all()
        print(num_types, types_incidents) 

        incidents = defaultdict(list)
        print(num_alert) 
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
            sch = ScheduleItems.query.filter(ScheduleItems.dayOfWeek == day and ScheduleItems.type_id == incident_obj.type_id).first()
            url_inc = 'http://localhost:1080/incidents/'+str(incident_obj.id)
            message = 'Hurry! You have '+incident_obj.TypeOfIncident.typeName+' incidents! Check it here '+url_inc
            notification = NotificationRules(incident_id = incident_obj.id, scheduleItem_id = sch.id, body = message, interval = 1, status = True)
            db.session.add(notification)
            db.session.commit()
            print('[*] вхожу в функцию уведомления')
            # send_notification(incident_obj)

            send_notification(incident_obj, notification)
        return jsonify(data)
    return "no item"

@app.route('/incidents', methods=['GET', 'POST'])
# @login_required
def show_incidents():
    incidents=Incidents.query.all()

    return render_template('incidents.html', incidents=incidents) #ошибка тут!!!!


@app.route('/types_incidents', methods=['GET'])
# @login_required
def show_types():
    print('[*] Show types')
    on_types = TypeOfIncident.query.filter(TypeOfIncident.active == True).all()
    off_types = TypeOfIncident.query.filter(TypeOfIncident.active == False).all()
    return render_template('types.html', active=on_types, nonactive=off_types)

def send_notification(incident, notification_rule):
    print('[*] Внутри функции send_notification')
    # print('[*] Обращение к бд за контактами')
    contacts = ScheduleItems.query.filter(ScheduleItems.id == notification_rule.scheduleItem_id).first().channels
    # print('[*] Контакты и айди', contacts, incident.id)
    body = notification_rule.body

    for _, contact in enumerate(cycle(contacts.split())):

        print('[*] Sending to', contact)
        # url=contact
        # type = Channels.query.filter(Channels.channel_source_value == url).all().channel_source_type
        # send_message(type, url, body)
        
        time.sleep(30)
        # print('[*] Подключаемся к бд за новым статусом ')
        incident = Incidents.query.filter(Incidents.id == incident.id).first()
        db.session.commit()
        print('[*] After conn to DB status is ', incident.status)
        if incident.status!='Active':
            print('Hurrah! You.ve done it! Incident status is ', incident.status)
            break
    print('the end')
        


@app.route('/schedule', methods=['GET'])
# @login_required
def show_schedule():
    on_types = TypeOfIncident.query.filter(TypeOfIncident.active == True).all()
    off_types = TypeOfIncident.query.filter(TypeOfIncident.active == False).all()
    return render_template('schedule.html', active=on_types, nonactive=off_types)


@app.route('/types_incidents/create', methods=['POST','GET'])
def create_type():
    if request.method == 'POST':
        name = request.form['typeName']
        description = request.form['description']
        labels = request.form['labels']
        active = request.form['active']
        if active=='y':
            active=True
        else:
            active=False
        
        type = TypeOfIncident(typeName=name, description=description, labels=labels, active=active)
        db.session.add(type)
        db.session.commit()

        for day in range(1,8):
            schItem_obj = ScheduleItems(TypeOfIncident = type, dayOfWeek=day, channels =contact_list)
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
        db.session.flush()
        return redirect(url_for('show_types'))
    form = TypeForm(obj=type)
    return render_template('edit_type.html', type=type, form=form)

@app.route('/incidents/<id>', methods=['GET', 'POST'])
# @login_required
def show_incident(id):
    incident = Incidents.query.get(id)
    print('[*] Внутри конкретного инцидента')
   
    option_list=['Active', 'Work-in progress', 'Postponed', 'Done']
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
        if status=='Done':
            end = datetime.now()
            print('[*] Добавляю время')  
            notification = NotificationRules.query.filter(NotificationRules.incident_id == incident.id).first()
            db.session.delete(notification)
            db.session.commit
            incident.end = end
        if incident.user_id == None:
            print('[*] Добавляю юзера')
            incident.user_id= current_user.id
        print('[*] status after', incident.status)
        print('[*] Делаю коммит ', incident.status)
        db.session.commit()   

        return render_template('incident.html', incident=incident, option_list=option_list)
    return render_template('incident.html', incident=incident, option_list=option_list)



@app.after_request
def redirect_to_signin(response):
    if response.status_code == 401:
        return redirect(url_for('login_page') + '?next=' + request.url)
    return response

if __name__ == '__main__':
    db.create_all()
    app.run(host='0.0.0.0', port=1080, debug=True)