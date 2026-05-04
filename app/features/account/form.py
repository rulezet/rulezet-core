from flask import url_for
from flask_login import current_user
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import ValidationError
from wtforms.fields import (
    BooleanField, PasswordField, StringField,
    SubmitField, EmailField, TextAreaField
)
from wtforms.validators import Email, InputRequired, Length, Regexp, Optional, URL
from ...core.db_class.db import User


class LoginForm(FlaskForm):
    """Login form to connect"""
    email = EmailField('Email', validators=[InputRequired(), Email()])
    password = PasswordField('Password', validators=[InputRequired()])
    remember_me = BooleanField('Keep me logged in')
    submit = SubmitField('Log in')


class EditUserForm(FlaskForm):
    """Edit form to change user's information"""
    first_name = StringField('First name', validators=[InputRequired()])
    last_name = StringField('Last name', validators=[InputRequired()])
    email = EmailField('Email', validators=[InputRequired(), Email()])
    password = PasswordField(
        'Password',
        validators=[
            Optional(),
            Length(min=8, max=64, message="Password must be between 8 and 64 characters."),
            Regexp(r'.*[A-Z].*', message="Password must contain at least one uppercase letter."),
            Regexp(r'.*[a-z].*', message="Password must contain at least one lowercase letter."),
            Regexp(r'.*\d.*', message="Password must contain at least one digit.")
        ]
    )

    # --- NEW FIELDS ---
    username = StringField(
        'Username',
        validators=[
            Optional(),
            Length(min=3, max=64, message="Username must be between 3 and 64 characters."),
            Regexp(r'^[\w.-]+$', message="Username can only contain letters, digits, dots, hyphens and underscores.")
        ]
    )
    bio = TextAreaField(
        'Bio',
        validators=[Optional(), Length(max=500, message="Bio must be under 500 characters.")]
    )
    profile_picture = FileField(
        'Profile picture',
        validators=[
            Optional(),
            FileAllowed(['jpg', 'jpeg', 'png', 'gif', 'webp'], 'Images only.')
        ]
    )
    location = StringField(
        'Location',
        validators=[Optional(), Length(max=128)]
    )
    website_url = StringField(
        'Website',
        validators=[Optional(), Length(max=256)]
    )
    github_url = StringField(
        'GitHub',
        validators=[Optional(), Length(max=256)]
    )
    twitter_url = StringField(
        'Twitter / X',
        validators=[Optional(), Length(max=256)]
    )
    # --- END NEW FIELDS ---

    submit = SubmitField('Save changes')

    def validate_email(self, field):
        if field.data != current_user.email:
            if User.query.filter_by(email=field.data).first():
                raise ValidationError(
                    'Email already registered. (Did you mean to '
                    '<a href="{}">log in</a> instead?)'.format(url_for('account.index'))
                )

    def validate_username(self, field):
        if field.data:
            existing = User.query.filter_by(username=field.data).first()
            if existing and existing.id != current_user.id:
                raise ValidationError('This username is already taken.')


class AddNewUserForm(FlaskForm):
    """Creation form to create a user"""
    first_name = StringField('First name', validators=[InputRequired()])
    last_name = StringField('Last name', validators=[InputRequired()])
    email = StringField('Email', validators=[InputRequired(), Email(message="Please enter a valid email address.")])
    password = PasswordField(
        'Password',
        validators=[
            InputRequired(),
            Length(min=8, max=64, message="Password must be between 8 and 64 characters."),
            Regexp(r'.*[A-Z].*', message="Password must contain at least one uppercase letter."),
            Regexp(r'.*[a-z].*', message="Password must contain at least one lowercase letter."),
            Regexp(r'.*\d.*', message="Password must contain at least one digit.")
        ]
    )
    submit = SubmitField('Register')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError(
                'Email already registered. (Did you mean to '
                '<a href="{}">log in</a> instead?)'.format(url_for('account.index'))
            )