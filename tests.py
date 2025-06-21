from unittest import TestCase
from flask import session
from app import app
import ytmapi
from models import db, connect_db, User, Subscription, LikedVideo, Playlist, PlaylistVideo, Credential
import jwt
from flask_bcrypt import Bcrypt
import os

class IntegrationTests(TestCase):

    def setUp(self):
        app.config["TESTING"] = True
        app.config["DEBUG"] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()
        db.drop_all()
        db.create_all()
        bcrypt = Bcrypt()

        # user account for testing
        hash = bcrypt.generate_password_hash('testpass')
        hashutf = hash.decode("utf8")
        testuser = User(
                username = 'testuser',
                password_hash = hashutf
                )
        db.session.add(testuser)
        db.session.commit()

    def tearDown(self):
        with self.client.session_transaction() as sess:
            sess.clear()
        
    def test_security_signup(self):
        JWT_KEY = os.environ['JWT_KEY']
        signupTest = {
                'username' : 'signupTest',
                'password' : 'testpass',
                'privacyAgree' : 'on'
                }
        resp = self.client.post('/signup',data=signupTest, follow_redirects=True)
        html = resp.get_data(as_text=True)
        self.assertIn('Would you like to import some?', html)
        user = User.query.filter_by(username='signupTest').first_or_404()
        self.assertEqual('signupTest', user.username)
        with self.client.session_transaction() as sess:
            authtoken = sess['auth']
            authtoken = jwt.decode(authtoken, JWT_KEY)
            username = authtoken['user']
            self.assertEqual('signupTest', username)


    def test_security_login(self):
        JWT_KEY = os.environ['JWT_KEY']
        login = {
                'username' : 'testuser',
                'password' : 'testpass'
                }
        resp = self.client.post('/login',data=login, follow_redirects=True)
        html = resp.get_data(as_text=True)
        self.assertIn('Would you like to import some?', html)
        with self.client.session_transaction() as sess:
            authtoken = sess['auth']
            authtoken = jwt.decode(authtoken, JWT_KEY)
            username = authtoken['user']
            self.assertEqual('testuser', username)

    def test_security_logout(self):
        resp = self.client.get('/logout', follow_redirects=True)
        html = resp.get_data(as_text=True)
        self.assertIn('YouTube Data Migrator', html)
        with self.client.session_transaction() as sess:
            self.assertNotIn('auth', sess.keys())

    def test_save_subs(self):
        user = User.query.filter_by(username='testuser').first_or_404()
        substest = { "items": [ { "snippet": { "title": "Test Title One", "resourceId": { "channelId": "Test Channel ID One" }, "thumbnails": { "default": { "url": "https://example.com/one.jpg" } } } }, { "snippet": { "title": "Test Title Two", "resourceId": { "channelId": "Test Channel ID Two" }, "thumbnails": { "default": { "url": "https://example.com/two.jpg" } } } }, { "snippet": { "title": "Test Title Three", "resourceId": { "channelId": "Test Channel ID Three" }, "thumbnails": { "default": { "url": "https://example.com/three.jpg" } } } }, ] }
        ytmapi.save_subscriptions(substest, user)
        subslist = Subscription.query.filter_by(user_id=user.id).all()
        self.assertIn('Test Title', subslist[0].title)
        self.assertIn('Test Title', subslist[2].title)

    def test_save_likes(self):
        user = User.query.filter_by(username='testuser').first_or_404()
        likestest = { "items": [ { "id": "Test Video ID One", "snippet": { "title": "Test Video Title One", "thumbnails": { "default": { "url": "https://example.com/one.jpg" } }, "channelTitle": "Test Channel Title One" }, }, { "id": "Test Video ID Two", "snippet": { "title": "Test Video Title Two", "thumbnails": { "default": { "url": "https://example.com/two.jpg" } }, "channelTitle": "Test Channel Title Two" }, }, { "id": "Test Video ID Three", "snippet": { "title": "Test Video Title Three", "thumbnails": { "default": { "url": "https://example.com/three.jpg" } }, "channelTitle": "Test Channel Title Three" }, } ] } 
        ytmapi.save_liked_videos(likestest, user)
        likeslist = LikedVideo.query.filter_by(user_id=user.id).all()
        self.assertIn('Test Video Title', likeslist[0].title)
        self.assertIn('Test Video Title', likeslist[2].title)

    def test_save_playlists(self):
        user = User.query.filter_by(username='testuser').first_or_404()
        liststest = { "items": [ { "id": "Test Playlist ID One", "snippet": { "title": "Test Playlist Title One", "description": "Test description one", "thumbnails": { "default": { "url": "https://example.com/one.jpg" } } }, "status": { "privacyStatus": "private" } }, { "id": "Test Playlist ID Two", "snippet": { "title": "Test Playlist Title Two", "description": "Test description two", "thumbnails": { "default": { "url": "https://example.com/two.jpg" } } }, "status": { "privacyStatus": "private" } }, { "id": "Test Playlist ID Three", "snippet": { "title": "Test Playlist Title Three", "description": "Test description three", "thumbnails": { "default": { "url": "https://example.com/three.jpg" } } }, "status": { "privacyStatus": "private" } } ] }
        ytmapi.save_playlists(liststest, user)
        listslist = Playlist.query.filter_by(user_id=user.id).all()
        self.assertIn('Test Playlist Title', listslist[0].title)
        self.assertIn('Test Playlist Title', listslist[0].title)

    def test_delete_subs(self):
        user = User.query.filter_by(username='testuser').first_or_404()
        user_id = user.id
        substest = { "items": [ { "snippet": { "title": "Test Title One", "resourceId": { "channelId": "Test Channel ID One" }, "thumbnails": { "default": { "url": "https://example.com/one.jpg" } } } }, { "snippet": { "title": "Test Title Two", "resourceId": { "channelId": "Test Channel ID Two" }, "thumbnails": { "default": { "url": "https://example.com/two.jpg" } } } }, { "snippet": { "title": "Test Title Three", "resourceId": { "channelId": "Test Channel ID Three" }, "thumbnails": { "default": { "url": "https://example.com/three.jpg" } } } }, ] }
        ytmapi.save_subscriptions(substest, user)
        params = { 'Test Channel ID Onechannel':'on', 'Test Channel ID Threechannel':'on' }
        self.client.post('/delete',data=params, follow_redirects=True)
        subslist = Subscription.query.filter_by(user_id=user_id).all()
        self.assertEqual(1, len(subslist))

    def test_delete_likes(self):
        user = User.query.filter_by(username='testuser').first_or_404()
        user_id = user.id
        likestest = { "items": [ { "id": "Test Video ID One", "snippet": { "title": "Test Video Title One", "thumbnails": { "default": { "url": "https://example.com/one.jpg" } }, "channelTitle": "Test Channel Title One" }, }, { "id": "Test Video ID Two", "snippet": { "title": "Test Video Title Two", "thumbnails": { "default": { "url": "https://example.com/two.jpg" } }, "channelTitle": "Test Channel Title Two" }, }, { "id": "Test Video ID Three", "snippet": { "title": "Test Video Title Three", "thumbnails": { "default": { "url": "https://example.com/three.jpg" } }, "channelTitle": "Test Channel Title Three" }, } ] } 
        ytmapi.save_liked_videos(likestest, user)
        params = { 'Test Video ID Onevideoid':'on', 'Test Video ID Threevideoid':'on' }
        self.client.post('/delete',data=params, follow_redirects=True)
        likeslist = LikedVideo.query.filter_by(user_id=user_id).all()
        self.assertEqual(1, len(likeslist))

    def test_delete_playlists(self):
        user = User.query.filter_by(username='testuser').first_or_404()
        user_id = user.id
        liststest = { "items": [ { "id": "Test Playlist ID One", "snippet": { "title": "Test Playlist Title One", "description": "Test description one", "thumbnails": { "default": { "url": "https://example.com/one.jpg" } } }, "status": { "privacyStatus": "private" } }, { "id": "Test Playlist ID Two", "snippet": { "title": "Test Playlist Title Two", "description": "Test description two", "thumbnails": { "default": { "url": "https://example.com/two.jpg" } } }, "status": { "privacyStatus": "private" } }, { "id": "Test Playlist ID Three", "snippet": { "title": "Test Playlist Title Three", "description": "Test description three", "thumbnails": { "default": { "url": "https://example.com/three.jpg" } } }, "status": { "privacyStatus": "private" } } ] }
        ytmapi.save_playlists(liststest, user)
        params = { 'Test Playlist ID Oneplaylis':'on', 'Test Playlist ID Threeplaylis':'on' }
        self.client.post('/delete',data=params, follow_redirects=True)
        listslist = Playlist.query.filter_by(user_id=user_id).all()
        self.assertEqual(1, len(listslist))

    def test_delete_account(self):
        self.client.post('/delacc', follow_redirects=True)
        user = User.query.filter_by(username='testuser').all()
        self.assertEqual(0, len(user))

    def test_cascade_user(self):
        user = User.query.filter_by(username='testuser').first_or_404()
        user_id = user.id
        likestest = { "items": [ { "id": "Test Video ID One", "snippet": { "title": "Test Video Title One", "thumbnails": { "default": { "url": "https://example.com/one.jpg" } }, "channelTitle": "Test Channel Title One" }, }, { "id": "Test Video ID Two", "snippet": { "title": "Test Video Title Two", "thumbnails": { "default": { "url": "https://example.com/two.jpg" } }, "channelTitle": "Test Channel Title Two" }, }, { "id": "Test Video ID Three", "snippet": { "title": "Test Video Title Three", "thumbnails": { "default": { "url": "https://example.com/three.jpg" } }, "channelTitle": "Test Channel Title Three" }, } ] } 
        ytmapi.save_liked_videos(likestest, user)
        liststest = { "items": [ { "id": "Test Playlist ID One", "snippet": { "title": "Test Playlist Title One", "description": "Test description one", "thumbnails": { "default": { "url": "https://example.com/one.jpg" } } }, "status": { "privacyStatus": "private" } }, { "id": "Test Playlist ID Two", "snippet": { "title": "Test Playlist Title Two", "description": "Test description two", "thumbnails": { "default": { "url": "https://example.com/two.jpg" } } }, "status": { "privacyStatus": "private" } }, { "id": "Test Playlist ID Three", "snippet": { "title": "Test Playlist Title Three", "description": "Test description three", "thumbnails": { "default": { "url": "https://example.com/three.jpg" } } }, "status": { "privacyStatus": "private" } } ] }
        ytmapi.save_playlists(liststest, user)
        substest = { "items": [ { "snippet": { "title": "Test Title One", "resourceId": { "channelId": "Test Channel ID One" }, "thumbnails": { "default": { "url": "https://example.com/one.jpg" } } } }, { "snippet": { "title": "Test Title Two", "resourceId": { "channelId": "Test Channel ID Two" }, "thumbnails": { "default": { "url": "https://example.com/two.jpg" } } } }, { "snippet": { "title": "Test Title Three", "resourceId": { "channelId": "Test Channel ID Three" }, "thumbnails": { "default": { "url": "https://example.com/three.jpg" } } } }, ] }
        ytmapi.save_subscriptions(substest, user)
        self.client.post('/delacc', follow_redirects=True)
        subslist = Subscription.query.filter_by(user_id=user_id).all()
        self.assertEqual(0, len(subslist))
        likeslist = LikedVideo.query.filter_by(user_id=user_id).all()
        self.assertEqual(0, len(likeslist))
        listslist = Playlist.query.filter_by(user_id=user_id).all()
        self.assertEqual(0, len(listslist))

    def test_cascade_playlist(self):
        user = User.query.filter_by(username='testuser').first_or_404()
        user_id = user.id
        liststest = { "items": [ { "id": "Test Playlist ID One", "snippet": { "title": "Test Playlist Title One", "description": "Test description one", "thumbnails": { "default": { "url": "https://example.com/one.jpg" } } }, "status": { "privacyStatus": "private" } }, { "id": "Test Playlist ID Two", "snippet": { "title": "Test Playlist Title Two", "description": "Test description two", "thumbnails": { "default": { "url": "https://example.com/two.jpg" } } }, "status": { "privacyStatus": "private" } }, { "id": "Test Playlist ID Three", "snippet": { "title": "Test Playlist Title Three", "description": "Test description three", "thumbnails": { "default": { "url": "https://example.com/three.jpg" } } }, "status": { "privacyStatus": "private" } } ] }
        ytmapi.save_playlists(liststest, user)
        for playlist in liststest['items']:
            playlist_id = playlist['id']
            dbPlaylist = Playlist.query.filter_by(resource_id=playlist_id).first_or_404()
            playlist_items = { "items": [ { "snippet": { "resourceId": { "videoId": "Test Video Id One" } } }, { "snippet": { "resourceId": { "videoId": "Test Video Id Two" } } }, { "snippet": { "resourceId": { "videoId": "Test Video Id Three" } } } ] }
            ytmapi.save_playlist_items(playlist_items, dbPlaylist.id)
        params = { 'Test Playlist ID Oneplaylis':'on', 'Test Playlist ID Threeplaylis':'on' }
        self.client.post('/delete',data=params, follow_redirects=True)
        playlist_two = Playlist.query.filter_by(resource_id='Test Playlist ID Two').first_or_404()
        playlist_items_two = PlaylistVideo.query.filter_by(playlist_id=playlist_two.id).all()
        self.assertEqual(3, len(playlist_items_two))
        all_playlist_items = PlaylistVideo.query.all()
        self.assertEqual(3, len(all_playlist_items))
        all_playlists = Playlist.query.filter_by(user_id=user_id).all()
        self.assertEqual(1, len(all_playlists))


    def test_dashboard_subs(self):
        user = User.query.filter_by(username='testuser').first_or_404()
        user_id = user.id
        substest = { "items": [ { "snippet": { "title": "Test Title One", "resourceId": { "channelId": "Test Channel ID One" }, "thumbnails": { "default": { "url": "https://example.com/one.jpg" } } } }, { "snippet": { "title": "Test Title Two", "resourceId": { "channelId": "Test Channel ID Two" }, "thumbnails": { "default": { "url": "https://example.com/two.jpg" } } } }, { "snippet": { "title": "Test Title Three", "resourceId": { "channelId": "Test Channel ID Three" }, "thumbnails": { "default": { "url": "https://example.com/three.jpg" } } } }, ] }
        ytmapi.save_subscriptions(substest, user)
        resp = self.client.get('/dashboard', follow_redirects=True)
        html = resp.get_data(as_text=True)
        self.assertIn('Test Title Two', html)

    def test_dashboard_likes(self):
        user = User.query.filter_by(username='testuser').first_or_404()
        user_id = user.id
        likestest = { "items": [ { "id": "Test Video ID One", "snippet": { "title": "Test Video Title One", "thumbnails": { "default": { "url": "https://example.com/one.jpg" } }, "channelTitle": "Test Channel Title One" }, }, { "id": "Test Video ID Two", "snippet": { "title": "Test Video Title Two", "thumbnails": { "default": { "url": "https://example.com/two.jpg" } }, "channelTitle": "Test Channel Title Two" }, }, { "id": "Test Video ID Three", "snippet": { "title": "Test Video Title Three", "thumbnails": { "default": { "url": "https://example.com/three.jpg" } }, "channelTitle": "Test Channel Title Three" }, } ] } 
        ytmapi.save_liked_videos(likestest, user)
        resp = self.client.get('/dashboard', follow_redirects=True)
        html = resp.get_data(as_text=True)
        self.assertIn('Test Video Title One', html)

    def test_dashboard_playlists(self):
        user = User.query.filter_by(username='testuser').first_or_404()
        user_id = user.id
        liststest = { "items": [ { "id": "Test Playlist ID One", "snippet": { "title": "Test Playlist Title One", "description": "Test description one", "thumbnails": { "default": { "url": "https://example.com/one.jpg" } } }, "status": { "privacyStatus": "private" } }, { "id": "Test Playlist ID Two", "snippet": { "title": "Test Playlist Title Two", "description": "Test description two", "thumbnails": { "default": { "url": "https://example.com/two.jpg" } } }, "status": { "privacyStatus": "private" } }, { "id": "Test Playlist ID Three", "snippet": { "title": "Test Playlist Title Three", "description": "Test description three", "thumbnails": { "default": { "url": "https://example.com/three.jpg" } } }, "status": { "privacyStatus": "private" } } ] }
        ytmapi.save_playlists(liststest, user)
        resp = self.client.get('/dashboard', follow_redirects=True)
        html = resp.get_data(as_text=True)
        self.assertIn('Test Playlist Title One', html)
