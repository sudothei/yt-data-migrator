from waitress import serve
from flask import Flask, render_template, request, redirect, session, flash, send_file
from forms import AddLoginForm, AddSignUpForm, AddDelAccForm, AddSelectionForm, AddImportForm
from models import db, connect_db, User, Subscription, LikedVideo, Playlist, PlaylistVideo, Credential
from flask_bcrypt import Bcrypt
import datetime
import jwt
from functools import wraps
import os
import ytmapi
import json
import tempfile

app = Flask(__name__)

# Get secrets from environment
app.config["SECRET_KEY"] = os.environ['FLASK_KEY']
JWT_KEY = os.environ['JWT_KEY']
DATABASE_URL = os.environ['DATABASE_URL']
PORT = os.environ['PORT']

# App config
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = True
SESSION_COOKIE_SAMESITE = 'Strict'

bcrypt = Bcrypt()

connect_db(app)
db.create_all()

def get_session_user():
    """
    Returns the username from the session as a string
    """

    if app.config['TESTING'] == True:
        return 'testuser'
    # Check token for username
    authtoken = session['auth']
    authtoken = jwt.decode(authtoken, JWT_KEY)
    username = authtoken['user']
    return username

def get_user(username):
    """
    Returns a user object
    """

    user = User.query.filter_by(username=username).first_or_404()
    return user

def create_login_token(username):
    """
    Save login session to JWT token
    """

    token = {
            'user' : username,
            'exp' : datetime.datetime.utcnow() + datetime.timedelta(days=14),
            }
    jwttoken = jwt.encode(token, JWT_KEY)
    session['auth'] = jwttoken
    return

def login_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs): 
        """
        Checks if username in JWT token is correct or sends to login screen
        """
        try:
            username = get_session_user()
            user = get_user(username)
            if user.username == username:
                return function()
            else:
                return redirect('/login')
        except:
            return redirect('/login')
        return redirect('/login')

    return wrapper

@app.route('/')
def mainpage():
    return render_template('welcome.html')

@app.route('/learnmore')
def learnmore():
    return render_template('learnmore.html')

@app.route('/privacy')
def privacyPolicy():
    return render_template('privacy_policy.html')

@app.route('/login', methods=["GET", "POST"])
def login():
    """
    Login page and form logic
    """

    # Dictionary for potential login errors
    errors = {
            'username' : {
                'error' : '',
                'labelclass' : '',
                'icon' : ''
                },
            'password' : {
                'error' : '',
                'labelclass' : '',
                'icon' : ''
                }
            }
    form = AddLoginForm()

    # Check for CSRF
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data

        # User in database check
        try:
            user = get_user(username)

            # Password correct check
            if bcrypt.check_password_hash(user.password_hash, password):
                # Provide user login token
                create_login_token(username)
                return redirect("/dashboard")
            else:
                errors['password']['error'] = 'Password is incorrect!'
                errors['password']['labelclass'] = 'mdc-text-field--invalid'
                errors['password']['icon'] = 'error'
        except:
            errors['username']['error'] = 'User does not exist!'
            errors['username']['labelclass'] = 'mdc-text-field--invalid'
            errors['username']['icon'] = 'error'
    return render_template('login.html', form=form, errors=errors)

@app.route('/signup', methods=["GET", "POST"])
def signup():
    """
    Sign-Up page and form logic
    """

    # Template for potential login errors
    errors = {
            'username' : {
                'error' : '',
                'labelclass' : '',
                'icon' : ''
                },
            }

    # Check for CSRF
    form = AddSignUpForm()
    if form.validate_on_submit():

        # Get form values
        username = form.username.data
        password = form.password.data
        privacyAgree = form.privacyAgree.data

        # Check if user already exists
        try:
            userExists = get_user(username)
            if bool(userExists):
                userExists = True
        except:
            userExists = False

        # Error message for a missing user
        if userExists:
            errors['username']['error'] = 'User already exists!'
            errors['username']['labelclass'] = 'mdc-text-field--invalid'
            errors['username']['icon'] = 'error'

        # Condition for valid input
        if not userExists and privacyAgree:
            # Hash password
            hash = bcrypt.generate_password_hash(password)
            hashutf = hash.decode("utf8")

            # Save user to database
            newuser = User(
                    username = username,
                    password_hash = hashutf
                    )
            db.session.add(newuser)
            db.session.commit()

            # Generate login token
            create_login_token(username)
            return redirect("/dashboard")

        return render_template('signup.html', form=form, errors=errors)
    else:
        return render_template('signup.html', form=form, errors=errors)


@app.route('/auth/google/signin')
@login_required
def authenticate():
    """
    Redirects to OAuth 2.0 flow link
    """

    # Generate authorization_url and state token
    authorization_url = ytmapi.get_authorization_url()

    # Save current state to user's session
    session['state'] = authorization_url[1]
    url = authorization_url[0]

    return redirect(url)

@app.route('/auth/google/callback')
@login_required
def auth():
    """
    OAuth 2.0 flow callback logic
    """

    # Ensure that the request is not a forgery and that the user sending this connect request is the expected user.
    if request.args.get('state', '') != session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'

        return response

    # Retreive auth code from query or return error
    auth_code = request.args.get('code', '')
    if auth_code == '':
        response = make_response(json.dumps(request.args['error']), 401)
        response.headers['Content-Type'] = 'application/json'

        return response

    # Turn auth code into an access token
    state = request.args['state']

    # Grab user info
    username = get_session_user()
    user = get_user(username)

    # Pass access token to api client
    credentials = ytmapi.get_access_token(auth_code, state)
    ytmapi.save_credentials(credentials, user)

    return 'Account successfully linked. You may now close this window.'

@app.route('/dashboard')
@login_required
def dashboard():
    """
    Main application interface
    """

    # Grab user info
    username = get_session_user()
    user = get_user(username) 

    # Grab user's data
    likeslist = LikedVideo.query.filter_by(user_id=user.id).all()
    subslist = Subscription.query.filter_by(user_id=user.id).all()
    playlistlist = Playlist.query.filter_by(user_id=user.id).all()

    # Add forms
    delAccForm = AddDelAccForm()
    selectionForm = AddSelectionForm()
    importForm = AddImportForm()

    return render_template('dashboard.html', subs=subslist, likes=likeslist, playlists=playlistlist, delAccForm=delAccForm, selectionForm=selectionForm, importForm=importForm)

@app.route('/delacc', methods=["POST"])
@login_required
def delAcc():
    """
    Form route for deleting user from database
    """

    # Check for CSRF
    delAccForm = AddDelAccForm()
    if delAccForm.validate_on_submit():

        # Grab user info
        username = get_session_user()
        user = get_user(username)

        # Delete user from DB
        db.session.delete(user)
        db.session.commit()

    return redirect("/")

@app.route('/delete', methods=["POST"])
@login_required
def deleteSelection():
    """
    Form route for deleting selected data from database
    """

    # Check for CSRF
    selectionform = AddSelectionForm()
    if selectionform.validate_on_submit():

        # Grab user info
        username = get_session_user()
        user = get_user(username)

        # Grab form data
        items = request.form.to_dict()
        try:
            items.pop("csrf_token")
        except:
            pass

        # Query items and delete from database
        for item in items.keys():
            if item[-7:] == 'videoid':
                LikedVideo.query.filter_by(user_id=user.id).filter_by(video_id=item[:-7]).delete()
            elif item[-7:] == 'channel':
                Subscription.query.filter_by(user_id=user.id).filter_by(channel_id=item[:-7]).delete()
            elif item[-7:] == 'playlis':
                playlist = Playlist.query.filter_by(user_id=user.id).filter_by(resource_id=item[:-7]).first_or_404()
                db.session.delete(playlist)
        db.session.commit()

    return redirect("/dashboard")

@app.route('/logout')
@login_required
def logout():
    """
    Link to log out
    """

    # Remove JWT login token
    session.clear()
    return redirect('/')

@app.route('/import', methods=["POST"])
@login_required
def importData():
    """
    Form route for importing selected data
    """

    # Check for CSRF
    importForm = AddImportForm()
    if importForm.validate_on_submit():

        # Grab user info
        username = get_session_user()
        user = get_user(username)

        # Run api client imports for selected categories
        if importForm.subscriptions.data:
            ytmapi.import_subscriptions(user)
        if importForm.likedVideos.data:
            ytmapi.import_liked_videos(user)
        if importForm.playlists.data:
            ytmapi.import_playlists(user)

    return redirect('/dashboard')

@app.route("/download-json", methods=["POST"])
@login_required
def downloadJson():
    """
    Form route to download selected data as a file
    """

    # Check for CSRF
    selectionform = AddSelectionForm()
    if selectionform.validate_on_submit():

        # Grab user info
        username = get_session_user()
        user = get_user(username)

        # Grab form data
        items = request.form.to_dict()

        # Query items from form and put into dictionary
        items.pop("csrf_token")
        data = {
                "liked_videos":[],
                "subscriptions":[],
                "playlists":[]
                }
        for item in items.keys():
            if item[-7:] == 'videoid':
                video = LikedVideo.query.filter_by(user_id=user.id).filter_by(video_id=item[:-7]).first_or_404()
                videoDict = {
                        'channel_title' : video.channel_title,
                        'video_title' : video.title,
                        'video_id' : video.video_id
                        }
                data['liked_videos'].append(videoDict)
            elif item[-7:] == 'channel':
                channel = Subscription.query.filter_by(user_id=user.id).filter_by(channel_id=item[:-7]).first_or_404()
                channelDict = {
                        'channel_title' : channel.title,
                        'channel_id' : channel.channel_id
                        }
                data['subscriptions'].append(channelDict)
            elif item[-7:] == 'playlis':
                playlist = Playlist.query.filter_by(user_id=user.id).filter_by(resource_id=item[:-7]).first_or_404()
                playlist_items = PlaylistVideo.query.filter_by(playlist_id=playlist.id).all()
                playlist_contents = list(map(lambda x: x.video_id, playlist_items))
                playlistDict = {
                        'playlist_title' : playlist.title,
                        'privacy_status' : playlist.privacy_status,
                        'playlist_id' : playlist.resource_id,
                        'playlist_items' : playlist_contents
                        }
                data['playlists'].append(playlistDict)

        # Make tempfile and write dictionary as JSON
        fd, filepath = tempfile.mkstemp()
        with os.fdopen(fd, "w") as f:
            json.dump(data, f)

    return send_file(filepath, as_attachment=True, attachment_filename="Your_YouTube_Data.json")

@app.route("/export", methods=["POST"])
@login_required
def exportData():
    """
    Form route to export selected data
    """

    # Check for CSRF
    selectionform = AddSelectionForm()
    if selectionform.validate_on_submit():

        # Grab user info
        username = get_session_user()
        user = get_user(username)

        # Grab form data
        items = request.form.to_dict()
        items.pop("csrf_token")

        # Query items from form and export using api client
        for item in items.keys():
            if item[-7:] == 'videoid':
                video = LikedVideo.query.filter_by(user_id=user.id).filter_by(video_id=item[:-7]).first_or_404()
                ytmapi.export_rating(video, user)
            elif item[-7:] == 'channel':
                channel = Subscription.query.filter_by(user_id=user.id).filter_by(channel_id=item[:-7]).first_or_404()
                try:
                    ytmapi.export_subscription(channel, user)
                except:
                    pass
            elif item[-7:] == 'playlis':
                playlist = Playlist.query.filter_by(user_id=user.id).filter_by(resource_id=item[:-7]).first_or_404()
                response = ytmapi.export_playlist(playlist, user)
                playlist_items = PlaylistVideo.query.filter_by(playlist_id=playlist.id).all()
                playlist_contents = list(map(lambda x: x.video_id, playlist_items))
                for videoId in playlist_contents:
                    ytmapi.export_playlist_vid(videoId, response['id'], user)

    return redirect('/dashboard')

# Web Server
serve(app, port=PORT)
