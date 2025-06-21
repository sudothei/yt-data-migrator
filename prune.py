from models import db, connect_db, User, Subscription, LikedVideo, Playlist, PlaylistVideo, Credential
import datetime
import os
from flask import Flask

app = Flask(__name__)

DATABASE_URL = os.environ['DATABASE_URL']
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = True
connect_db(app)
db.create_all()

timenow = datetime.datetime.utcnow().timestamp()
vids = LikedVideo.query.filter(LikedVideo.expiration_date <= timenow).all()
for vid in vids:
    db.session.delete(vid)
subs = Subscription.query.filter(Subscription.expiration_date <= timenow).all()
for sub in subs:
    db.session.delete(sub)
lists = Playlist.query.filter(Playlist.expiration_date <= timenow).all()
for plist in lists:
    db.session.delete(plist)

db.session.commit()
