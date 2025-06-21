from flask_sqlalchemy import SQLAlchemy
import datetime

db = SQLAlchemy()

def connect_db(app):
    """Connect to database."""

    db.app = app
    db.init_app(app)

class User(db.Model):
    """User."""

    __tablename__ = "users"

    id = db.Column( db.Integer, primary_key=True, autoincrement=True)
    username = db.Column( db.Text, nullable=False)
    password_hash = db.Column( db.Text, nullable=False)
    subscriptions = db.relationship('Subscription', backref='users', cascade='all, delete-orphan')
    liked_videos = db.relationship('LikedVideo', backref='users', cascade='all, delete-orphan')
    playlists = db.relationship('Playlist', backref='users', cascade='all, delete-orphan')
    credentials = db.relationship('Credential', backref='users', cascade='all, delete-orphan')

class Subscription(db.Model):
    """Subscription."""

    __tablename__ = "subscriptions"

    id = db.Column( db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column( db.Integer, db.ForeignKey('users.id'))
    channel_id = db.Column( db.Text, nullable=False)
    title = db.Column( db.Text, nullable=False)
    thumbnail = db.Column( db.Text, nullable=False)
    expiration_date = db.Column( db.Float, nullable=False )

class LikedVideo(db.Model):
    """liked Video."""

    __tablename__ = "liked_videos"

    id = db.Column( db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column( db.Integer, db.ForeignKey('users.id'))
    video_id = db.Column( db.Text, nullable=False)
    title = db.Column( db.Text, nullable=False)
    channel_title = db.Column( db.Text, nullable=False)
    thumbnail = db.Column( db.Text, nullable=False)
    expiration_date = db.Column( db.Float, nullable=False )

class Playlist(db.Model):
    """Playlist."""

    __tablename__ = "playlists"

    id = db.Column( db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column( db.Integer, db.ForeignKey('users.id'))
    resource_id = db.Column( db.Text, nullable=False)
    title = db.Column( db.Text, nullable=False)
    thumbnail = db.Column( db.Text, nullable=False)
    privacy_status = db.Column( db.Text, nullable=False)
    playlist_videos = db.relationship('PlaylistVideo', backref='playlists', cascade='all, delete-orphan')
    expiration_date = db.Column( db.Float, nullable=False )

class PlaylistVideo(db.Model):
    """PlaylistVideo."""

    __tablename__ = "playlist_videos"

    id = db.Column( db.Integer, primary_key=True, autoincrement=True)
    playlist_id = db.Column( db.Integer, db.ForeignKey('playlists.id', ondelete="CASCADE"))
    video_id = db.Column( db.Text, nullable=False)

class Credential(db.Model):
    """Credential."""

    __tablename__ = "credentials"

    id = db.Column( db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column( db.Integer, db.ForeignKey('users.id'), primary_key=True)
    token = db.Column( db.Text, nullable=False)
    refresh_token = db.Column( db.Text, nullable=False)
