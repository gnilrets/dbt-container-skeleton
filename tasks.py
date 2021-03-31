import os
import json
import pathlib

from invoke import task
from cryptography.fernet import Fernet

CONFIG_FILENAME='.config.env'
SECRET_KEY_FILENAME=os.path.join(pathlib.Path.home(), '.dbt-container-skeleton')

def get_secret_key():
    'Returns the users secret key.  Creates a new one if necessary'

    if not os.path.exists(SECRET_KEY_FILENAME):
        key = Fernet.generate_key()
        with open(SECRET_KEY_FILENAME, 'wb') as key_file:
            key_file.write(key)

    return open(SECRET_KEY_FILENAME, 'rb').read()


def read_config():
    'Reads the encrypted configuration file'

    fencrypt = Fernet(get_secret_key())

    if not os.path.exists(CONFIG_FILENAME):
        return {}

    with open(CONFIG_FILENAME, 'rb') as config_file:
        config = json.loads(fencrypt.decrypt(config_file.read()))
    return config

def write_config(config):
    'Writes the encrypted configuration file'

    fencryptor = Fernet(get_secret_key())

    with open(CONFIG_FILENAME, 'wb') as config_file:
        config_file.write(
            fencryptor.encrypt(json.dumps(config).encode())
        )

@task
def config_show(ctx):
    'Shows the current dbt container configuration (SECRETS IN PLAINTEXT)'

    print(json.dumps(read_config(), indent=4))


@task
def config(ctx):
    'Set dbt container configuration and environment variables'


    with open('config_template.env') as template_file:
        file_lines = template_file.readlines()
        config_template = {}
        for l in file_lines:
            l = l.strip()
            if len(l) == 0 or l[0] == '#':
                continue
            key, value = l.split('=', 1)
            config_template[key] = value

    config = {**config_template, **read_config()}

    print('NOTE: Press enter at any time to accept the default or existing value. Use "None" to indicate Null/None')
    for key, value in config.items():
        user_value = input('{} ({}): '.format(key, '***' + (value or '')[-3:]))
        config[key] = user_value or config[key]
        if user_value == 'None':
            config[key] = None

    write_config(config)

@task
def requirements_compile(ctx):
    '''
    Compile Python requirements without upgrading.
    Docker images need to be rebuilt after running this.
    '''

    ctx.run('pip-compile requirements.in')

@task
def requirements_upgrade(ctx):
    '''
    Compile Python requirements with upgrading.
    Docker images need to be rebuilt after running this.
    '''

    ctx.run('pip-compile -U requirements.in')

@task
def build(ctx):
    'Build the dbt runner container'

    ctx.run(f'docker build -t dbt-runner -f Dockerfile .')

@task
def dbt_shell(ctx, args=''):
    'Open a shell to the dbt runner container'

    config = read_config()
    envs = []
    for key, value in config.items():
        os.environ[key] = value or ''
        envs.append(key)

    envs_str = ' '.join(['--env ' + env for env in envs])
    ctx.run(f'docker run --rm -it {envs_str} -v ${{PWD}}:/dbt-runner -w /dbt-runner/dbt {args} dbt-runner /bin/bash')
