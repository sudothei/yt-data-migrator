from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField

class AddLoginForm(FlaskForm):
    """Form for logging in"""
    username = StringField("Username")
    password = PasswordField("Password")

class AddSignUpForm(FlaskForm):
    """Form for signing up"""
    username = StringField("Username")
    password = PasswordField("Password")
    privacyAgree = BooleanField("Privacy Agreement")

class AddDelAccForm(FlaskForm):
    """Form to delete account"""

class AddSelectionForm(FlaskForm):
    """Form to handle delete and export selections"""

class AddImportForm(FlaskForm):
    """Form to select import data"""
    subscriptions = BooleanField("Subscriptions")
    likedVideos = BooleanField("Liked Videos")
    playlists = BooleanField("Your Playlists")
