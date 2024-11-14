# app/forms.py

from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField, SelectField
from wtforms.validators import DataRequired, NumberRange

class AnswerForm(FlaskForm):
    answer = StringField('', validators=[DataRequired()], render_kw={"autocomplete": "off"})
    submit = SubmitField('Check')

class CreateCourseForm(FlaskForm):
    topic = StringField('', validators=[DataRequired()], render_kw={"autocomplete": "off", "placeholder": "Learn anything..."})
    num_lessons = SelectField('Number of Lessons',
                            choices=[(str(i), str(i)) for i in range(1, 7)],
                            validators=[DataRequired()])
    next_button = SubmitField('➡️ Next')
    generate_button = SubmitField('🚀 Create Outline')

class FeedbackForm(FlaskForm):
    feedback = TextAreaField('', validators=[DataRequired()], render_kw={"placeholder": "Ask anything to craft your perfect course..."})
    submit = SubmitField('Regenerate Outline')

class ConfirmForm(FlaskForm):
    submit = SubmitField('🚀 Start learning')
