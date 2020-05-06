from wtforms import Form, StringField, TextAreaField, BooleanField, IntegerField
from wtforms.validators import DataRequired

class TypeForm(Form):
    typeName = StringField('Type', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[DataRequired()])
    labels = TextAreaField('Labels', validators=[DataRequired()])
    active = BooleanField('Active')
    interval = IntegerField('Time between messages (in minutes)', validators=[DataRequired()])

    
class SearchForm(Form):
    search = StringField('search', validators=[DataRequired()])