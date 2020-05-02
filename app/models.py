from alertapp import db
from enum import Enum

class Alerts(db.Model):

    __tablename__ = 'alerts'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    alertname = db.Column(db.String(64), unique=False, nullable=False)
    resource = db.Column(db.String(64), unique=False, nullable=False)
    message = db.Column(db.Text, unique=False, nullable=False)
    severity = db.Column(db.String(64), nullable=False)
    incident_id =  db.Column(db.Integer, db.ForeignKey('Incidents.id'), nullable=False)



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
    start = db.Column(db.DateTime, nullable=False)
    end = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(30), nullable=False)
    user_id =  db.Column(db.Integer, db.ForeignKey('Users.id'), nullable=False)
    alerts = db.relationship('Alerts', backref='Incidents', lazy=True)



class Users(db.Model):

    __tablename__ = 'Users'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(60), nullable=False)
    fullName = db.Column(db.String(60), nullable=False)
    password = db.Column(db.String(260), nullable=False)
    incidents = incidents = db.relationship('Incidents', backref='Users', lazy=True)

# class Channels(db.Model):

#     __tablename__ = 'Channels'

#     id = db.Column(db.Integer, primary_key=True, autoincrement=True)
#     user_id =  db.Column(db.Integer, db.ForeignKey('Users.id'), nullable=False)
#     channel_source_type = db.Column(db.String(60), nullable=False) # probably should be in another table
#     channel_source_value = db.Column(db.String(150), nullable=False)


# class DayOfWeek(Enum):
#     monday = 1
#     tuesday = 2
#     wednesday = 3
#     thursday = 4
#     friday = 5
#     saturday = 6
#     sunday = 7

# class ScheduleItems(db.Model):

#     __tablename__ = 'ScheduleItems'

#     id = db.Column(db.Integer, primary_key=True, autoincrement=True)
#     type_id =  db.Column(db.Integer, db.ForeignKey('TypeOfIncident.id'), nullable=False)
#     # dayOfWeek = db.Column(db.Enum(DayOfWeek)) # probably doesn't work

#     duty_start = db.Column(db.DateTime, nullable=False)
#     duty_end = db.Column(db.DateTime, nullable=False)


# class ScheduleItemChannels(db.Model):
#     ScheduleItemId INTEGER REFERENCES ScheduleItem (Id),
#     ChannelId INTEGER REFERENCES Channels (Id)