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
def build(ctx):
    "Build the dbt runner container"

    ctx.run(
        f"docker-compose -f docker-compose.yml build dbt-runner"
    )


@task
def up(ctx):
    "Start the dbt runner container"

    ctx.run(
        f"docker-compose -f docker-compose.yml up -d dbt-runner"
    )



@task
def down(ctx):
    "stop all containers"

    ctx.run(f"docker-compose -f docker-compose.yml down")


def build_envs_arg():
    config = read_config()
    envs = []
    for key, value in config.items():
        os.environ[key] = value or ""
        envs.append(f"{key}={value}")
    envs_arg = " ".join(["-e " + env for env in envs])
    return envs_arg


def dbt_exec(command, docker_compose_args="", command_args=""):
    docker_service = "dbt-runner"
    envs_arg = build_envs_arg()

    if command == "shell":
        command = "/bin/bash"

    return f"docker-compose -f docker-compose.yml exec {envs_arg} --workdir /dbt-runner/dbt {docker_compose_args} {docker_service} {command} {command_args}"


@task
def dbt_shell(ctx, docker_args=""):
    """Open a bash shell in the dbt runner container"""
    ctx.run(dbt_exec("shell"))


@task(pre=[up])
def dbt_compile(ctx):
    """Run ``dbt compile`` in the dbt-runner container."""
    ctx.run(dbt_exec("dbt compile"))


@task(pre=[up])
def dbt_docs(ctx, no_compile=False):
    """Run ``dbt docs generate`` in the dbt-runner container."""
    command = "dbt docs generate"
    if no_compile is True:
        command += " --no-compile"
    ctx.run(dbt_exec(command))


@task(pre=[up])
def dbt_seed(ctx,):
    """Run ``dbt seed`` in the dbt-runner container."""
    ctx.run(dbt_exec("dbt seed"))


@task(pre=[up, dbt_seed])
def dbt_run(ctx):
    """Run ``dbt run`` in the dbt-runner container."""
    ctx.run(dbt_exec("dbt run"))


@task(pre=[up])
def dbt_test(ctx):
    """Run ``dbt test`` in the dbt-runner container."""
    ctx.run(dbt_exec("dbt test"))


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

@task()
def sql_shell(ctx):
    """Open a psql prompt, connected to the target database"""
    docker_service = "dbt-runner"
    envs_arg = build_envs_arg()

    config = read_config()

    # this sets the default search path so that commands like \dv just work
    envs_arg += ' -e PGOPTIONS="--search_path=public"'.format(
        **config
    )

    envs_arg += " -e PGPASSWORD={POSTGRES_PASSWORD}".format(**config)

    command = (
        "psql -h {POSTGRES_HOST} -U {POSTGRES_USER} -d {POSTGRES_DBNAME}".format(
            **config
        )
    )

    ctx.run(
        f"docker-compose -f docker-compose.yml exec {envs_arg} {docker_service} {command}"
    )

