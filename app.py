# coding=utf-8
import os
from flask import Flask, render_template, request, Response
from flask_bootstrap import Bootstrap
from flask.ext.httpauth import HTTPBasicAuth
import ldap

from raven.contrib.flask import Sentry
import logging
from werkzeug.contrib.fixers import ProxyFix

from config import config


app = Flask(__name__)
bootstrap = Bootstrap(app)
auth = HTTPBasicAuth()
sentry = Sentry()

if os.environ.get('CAMERAS_FLASK_ENV') == 'prod':
    app.config.from_object(config['production'])
    app.wsgi_app = ProxyFix(app.wsgi_app)
else:
    app.config.from_object(config['development'])
    sentry.init_app(app, logging=True, level=logging.DEBUG)


camera_dict = app.config['CAMERAS']


@auth.verify_password
def verify_camera_user(username, password):
    """
    Verify the user's password against LDAP server and confirm that they are in the correct group
    """
    app.logger.debug('Verify user: {username}'.format(username=username))
    Server = app.config['LDAP_SERVER']
    DN, Secret, un = username + '@banet.local', password, username

    Base = app.config['LDAP_BASE']
    Scope = ldap.SCOPE_SUBTREE
    Filter = "(&(objectClass=user)(sAMAccountName="+un+"))"
    Attrs = ["displayName","memberOf"]

    l = ldap.initialize(Server)
    l.set_option(ldap.OPT_REFERRALS, 0)
    l.protocol_version = 3

    try:
        l.simple_bind_s(DN, Secret)
    except:
        app.logger.warn('{username} failed to bind'.format(username=username))
        return False

    r = l.search(Base, Scope, Filter, Attrs)
    Type, user = l.result(r, 60)

    try:
        Name, Attrs = user[0]
    except IndexError:
        app.logger.warn('{username} failed to find attributes'.format(username=username))
        return False

    if hasattr(Attrs, 'has_key') and Attrs.has_key('displayName'):
        displayName = Attrs['displayName'][0]
        if hasattr(Attrs, 'has_key') and Attrs.has_key('memberOf'):
            if app.config['LDAP_GROUP'] in Attrs['memberOf']:
                app.logger.info('{username} sucessfully logged in'.format(username=username))
                return True

    app.logger.warn('{username} failed to login'.format(username=username))
    return False


@app.route('/')
@auth.login_required
def index():
    """
    Index page with list of cameras
    """
    app.logger.info('Rendering index for {username}'
                     .format(username=auth.username()))
    return render_template('index.html', camera_dict=camera_dict)


@app.route('/all')
@auth.login_required
def allcameras():
    """
    Load streams of all the cameras at once
    """
    app.logger.info('Rendering all cameras for {username}'
                     .format(username=auth.username()))
    return render_template('all.html',
                           camera_dict=camera_dict,
                           view_user=app.config['VIEW_USER'],
                           view_pass=app.config['VIEW_PASS'],
                           camera_base_url=app.config['CAMERA_BASE_URL'],
                           camera_view_path=app.config['CAMERA_VIEW_PATH'])


@app.route('/camera/<camera_name>')
@auth.login_required
def camerapage(camera_name):
    """
    Load stream of a single camera
    """
    app.logger.info('Rendering {camera_name} for {username}'
                     .format(camera_name=camera_name,
                             username=auth.username()))
    return render_template('camera.html',
                           camera_name=camera_name,
                           camera_dict=camera_dict,
                           camera_title=camera_dict[camera_name],
                           view_user=app.config['VIEW_USER'],
                           view_pass=app.config['VIEW_PASS'],
                           camera_base_url=app.config['CAMERA_BASE_URL'],
                           camera_view_path=app.config['CAMERA_VIEW_PATH'])


if __name__ == '__main__':
    app.run(debug=True)
