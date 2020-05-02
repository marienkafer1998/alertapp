#docker-compose up -d --build app

from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from collections import defaultdict
from datetime import datetime
# from models import Alerts, Incidents, TypeOfIncident, Users

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql+psycopg2://alertapp:alertapp@localhost/alertapp'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

from enum import Enum

class Alerts(db.Model):

    __tablename__ = 'Alerts'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    service = db.Column(db.String(64), unique=False, nullable=False)
    severity = db.Column(db.String(64), nullable=False)
    incident_id =  db.Column(db.Integer, db.ForeignKey('Incidents.id'), nullable=False)

    # def __init__(self, service, severity):
    #     self.service = service
    #     self.severity = severity


class TypeOfIncident(db.Model):

    __tablename__ = 'TypeOfIncident'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    typeName = db.Column(db.String(30), unique=True, nullable=False)
    description = db.Column(db.String(300), unique=True, nullable=False)
    labels = db.Column(db.Text, nullable=False) #instead of JSON and ARRAY
    incidents = db.relationship('Incidents', backref='TypeOfIncident', lazy=True)
    # schedule_items = db.relationship('ScheduleItems', backref='TypeOfIncident', lazy=True)

class Incidents(db.Model):

    __tablename__ = 'Incidents'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    type_id =  db.Column(db.Integer, db.ForeignKey('TypeOfIncident.id'), nullable=False)
    start = db.Column(db.DateTime, nullable=True)
    end = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(30), nullable=False)
    user_id =  db.Column(db.Integer, db.ForeignKey('Users.id'), nullable=True)
    alerts = db.relationship('Alerts', backref='Incidents', lazy=True)

    # def __init__(self, service, severity):
    
    #     self.id = id
    #     self.type_id = type_id
    #     self.start = start
    #     self.end = end
    #     self.status = status


class Users(db.Model):

    __tablename__ = 'Users'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(60), nullable=False)
    fullName = db.Column(db.String(60), nullable=False)
    password = db.Column(db.String(260), nullable=False)
    incidents = incidents = db.relationship('Incidents', backref='Users', lazy=True)



@app.route('/receive', methods=['POST', 'GET'])
def get_data():
    if request.method == 'POST':
        data = request.get_json()
        num_types = db.session.query(TypeOfIncident).count()
        num_alert = len(data)
        types_incidents = db.session.query(TypeOfIncident.id, TypeOfIncident.labels).all()
        print(num_types, types_incidents) 

        incidents = defaultdict(list)
        # types_incidents = [(1, 'database'), (2, 'server error')]
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
            incident_obj = Incidents(type_id = incident[0], start = datetime.now(), status = 'Active')
            db.session.add(incident_obj)
            db.session.commit()
            for alert in incident[1]:
                labels = alert['labels']
                alert_obj = Alerts(severity=labels['severity'], service=labels['service'], Incidents=incident_obj)
                db.session.add(alert_obj)
                db.session.commit()
        return jsonify(data)
    return "no item"

@app.route('/incidents', methods=['GET'])
def show_incidents():
    return render_template('incidents.html', incidents=Incidents.query.all())


if __name__ == '__main__':
    db.create_all()
    app.run(host='0.0.0.0', port=1080, debug=True)
