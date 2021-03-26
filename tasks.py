#TODO: Encrypt configuration file: https://levelup.gitconnected.com/encrypt-and-decrypt-files-using-python-python-programming-pyshark-a67774bbf9f4

from invoke import task

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
def dbt_shell(ctx):
    'Open a shell to the dbt runner container'

    ctx.run('docker run --rm -it -v ${PWD}:/dbt-runner -w /dbt-runner/dbt dbt-runner /bin/bash')
