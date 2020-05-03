from wtforms import Form, StringField, TextAreaField, BooleanField
from wtforms.validators import DataRequired

class TypeForm(Form):
    typeName = StringField('Type', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[DataRequired()])
    labels = TextAreaField('Labels', validators=[DataRequired()])
    active = BooleanField('Active')

    
