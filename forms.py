from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField, BooleanField, TextAreaField
from wtforms.validators import DataRequired, URL, Email, EqualTo
from flask_ckeditor import CKEditorField


# WTForm for creating a blog post
class CreatePostForm(FlaskForm):
    title = StringField("Blog Post Title", validators=[DataRequired()])
    subtitle = StringField("Subtitle", validators=[DataRequired()])
    img_url = StringField("Blog Image URL", validators=[DataRequired(), URL()])
    body = CKEditorField("Blog Content", validators=[DataRequired()])
    submit = SubmitField("Submit Post")


# TODO: Create a RegisterForm to register new users
class RegisterForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(),
                                                                     EqualTo('password',
                                                                             message='Passwords must match.')])

    name = StringField('Name', validators=[DataRequired()])
    logged_in = BooleanField('Keep me logged in')
    submit = SubmitField('SIGN ME UP!')


# TODO: Create a LoginForm to login existing users
class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    logged_in = BooleanField('Keep me logged in')
    submit = SubmitField('LET ME IN!')


# TODO: Create a CommentForm so users can leave comments below posts
class CommentForm(FlaskForm):
    comment = TextAreaField('Comment', validators=[DataRequired()])
    submit = SubmitField('SUBMIT COMMENT')
