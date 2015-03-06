"""
Fabfile to setup and deploy cameras-flask for Bridgton Academy
"""
from fabric.api import cd, run, local, env, sudo, put, prompt, lcd
from fabric.contrib.console import confirm
from fabtools import require
from fabtools.python import virtualenv
import fabtools

# uses a file called fabhosts where servers can be defined but gitignored
# looks like
# 
# from fabric.api import env
#
# def prod():
#   env.user = 'username'
#   env.hosts = ['server1', 'server2']
#
try:
    from fabhosts import prod
except ImportError:
    pass

local_app_dir = '.'
local_config_dir = local_app_dir + '/server-config'

www_user = 'cameras-flask'
www_folder = '/home/www/cameras-flask'
env_folder = '/home/www/env-cameras-flask/'

remote_git_dir = '/home/git'


def apt_upgrade():
    """
    Run apt-get upgrade
    """
    sudo('apt-get update')
    sudo('apt-get upgrade')


def create_user():
    """
    Create a camera_flask user for running cameras-flask
    """
    require.user(www_user, system=True)


def create_www_folder():
    """
    Create a directory to run cameras-flask from
    """
    require.directory(www_folder,
                      owner=www_user,
                      use_sudo=True)


def create_venv():
    """
    Create virtualenv for cameras-flask
    """
    require.python.virtualenv(env_folder,
                              use_sudo=True)


def put_requirements():
    """
    Put our code on the server
    """
    with cd(www_folder):
        require.file('requirements.txt', source='requirements.txt', use_sudo=True, owner=www_user)


def configure_git():
    """
    1. Setup bare Git repo
    2. Create post-receive hook
    """
    require.directory(remote_git_dir, use_sudo=True)
    with cd(remote_git_dir):
        run('pwd')
        #with lcd(local_config_dir):
        local('pwd')
        fabtools.files.upload_template(local_config_dir + '/post-receive', '.',
                                        use_sudo=True,
                                        use_jinja=True,
                                        context={'www_folder': www_folder})
        
    



def deploy():
    """
    Deploy code to server
    """
    local('git status')

    commit = confirm('Commit all changes?')
    if commit:
        local('git add -A')
        message = prompt('Commit message?')
        if message == '':
            local('git commit')
        else:
            local('git commit -m "{message}"'.format(message=message))






def install_packages():
    """
    Install required packages
    """
    require.deb.packages(['python-dev', 'libldap2-dev', 'libsasl2-dev', 'libssl-dev'])



def install_requirements():
    """
    Install requirements
    """
    with virtualenv(env_folder):
        with cd(www_folder):
            require.python.requirements('requirements.txt', use_sudo=True)


def bootstrap():
    """
    Setup all the things to make cameras-flask go
    """
    create_user()
    create_www_folder()
    create_venv()
    put_requirements()
    install_packages()
    install_requirements()


def copy_pubkey():
    """
    Copy public key to user on server's .ssh
    """
    local('ssh-copy-id {host}'.format(host=env.host_string))
