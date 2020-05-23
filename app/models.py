from flask import Flask, request, jsonify, render_template, flash, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from collections import defaultdict
from datetime import datetime
from flask_login import login_user, login_required, logout_user, UserMixin, LoginManager, current_user
from forms import TypeForm
from alertapp import db, manager


Labels = db.Table('Labels',
    db.Column('Alert_id', db.Integer, db.ForeignKey('Alerts.id')),
    db.Column('Label', db.String(60)),
    db.Column('Value', db.String(60))



class Alerts(db.Model):

    __tablename__ = 'Alerts'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    incident_id =  db.Column(db.Integer, db.ForeignKey('Incidents.id'), nullable=False)
    alertname = db.Column(db.String(64), unique=False, nullable=False)
    hash_id = db.Column(db.String(64), unique=True, nullable=False)
    alerts = db.relationship('Labels', backref=db.backref('alert'), lazy=True)



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


