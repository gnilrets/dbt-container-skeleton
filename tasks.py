import os
import json
import pathlib
import yaml
import getpass

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


def read_config_template():
    with open('config_template.env') as template_file:
        file_lines = template_file.readlines()
        config_template = {}
        for l in file_lines:
            l = l.strip()
            if len(l) == 0 or l[0] == '#':
                continue
            key, value = l.split('=', 1)
            config_template[key] = value
    return config_template


def read_env_template():
    with open('./env_template.yml', 'r') as template_file:
        env_template = yaml.safe_load(template_file)
    return env_template

def read_config():
    '''
    Reads the encrypted configuration file.
    If no file exists, fetches env vars from the host that are defined in the config template.
    '''

    fencrypt = Fernet(get_secret_key())

    if not os.path.exists(CONFIG_FILENAME):
        env_template = read_env_template()
        config = {
            var: os.environ.get(var, params['default'])
            for var, params in env_template['variables'].items()
        }
        return config

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
    env_template = read_env_template()

    config = {}
    current_config = read_config()
    print("---\n" + env_template['description'])
    for var, params in env_template['variables'].items():
        if params.get('user', True):
            print(f"-\n{var}: {params['description']}")
        current_value = current_config.get(var) or params['default'] or ''

        displayed_value = current_value
        input_func = input
        if params.get('secret', False):
            displayed_value = '***' + current_value[-3:]
            input_func = getpass.getpass

        user_value = None
        if params.get('user', True):
            user_value = input_func('{} (Currently: {}): '.format(var, displayed_value))

        config[var] = user_value or current_value

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
def build(ctx, ci=False):
    'Build the dbt runner container'

    cache_from_arg = '--cache-from=dbt-runner' if ci else ''
    ctx.run(f'docker build -t dbt-runner {cache_from_arg} -f Dockerfile .')


def docker_run_dbt_cmd(command, interactive=False, docker_args=''):
    config = read_config()
    envs = []
    for key, value in config.items():
        env_var = key.replace('*', '')

        # Existing environment variables override those defined in config file
        os.environ[env_var] = os.environ.get(env_var, value or '')
        envs.append(env_var)
    envs_arg = ' '.join(['--env ' + env for env in envs])

    project_root='/dbt-runner'
    mount_project_arg = f'-v ${{PWD}}:{project_root}'

    interactive_arg = ''
    if interactive:
        interactive_arg = '-it'

    return f'docker run --rm {interactive_arg} {envs_arg} {mount_project_arg} -w {project_root}/dbt {docker_args} dbt-runner {command}'


@task
def dbt_shell(ctx, docker_args=''):
    'Open a shell to the dbt runner container'
    ctx.run(docker_run_dbt_cmd(
        '/bin/bash',
        interactive=True,
        docker_args=docker_args
    ))

@task
def lint(ctx, docker_args='', ci=False):
    'Runs all linters'

    if ci:
        docker_args += '--network=host'

    ctx.run(docker_run_dbt_cmd(
    '"sqlfluff lint models"',
        interactive=False,
        docker_args=docker_args
    ))

@task
def init_test_db(ctx, docker_args='', ci=False):
    'Initializes the test database'

    if ci:
        docker_args += '--network=host'

    ctx.run(docker_run_dbt_cmd(
        '"dtspec db --init-test-db"',
        interactive=False,
        docker_args=docker_args
    ))

@task
def dtspec_test_dbt(ctx, docker_args='', ci=False):
    'Runs the dtspec dbt tests'

    if ci:
        docker_args += '--network=host'

    ctx.run(docker_run_dbt_cmd(
        '"dtspec test-dbt"',
        interactive=False,
        docker_args=docker_args
    ))
