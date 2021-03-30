# dbt container skeleton

This project is intended to be used as a way to bootstrap a
containerized dbt development environment.  This helps teams work
together by ensuring that everyone is using the same version of dbt
and its dependencies.


## Setup

Of course, you'll need to download and install [docker community
edition](https://www.docker.com/).  Additionally, you should be using
a Python environment mananger like
[miniconda](https://conda.io/miniconda.html).  After installing miniconda,
create a minconda environment for this project via

    conda create --name dbt-container-skeleton python=3.8

Then activate the environment (this will need to be done every time you open a new shell):

    conda activate dbt-container-skeleton

Next, install the Python packages needed to manage your dbt container via

    pip install -r host_requirements.txt

Build the dbt container via

    inv build

The example dbt project included assumes there is a Postgres database running on your
host machine.  To configure the credentials needed to connect to this database run

    inv config

This will ask you for your Postgres username and password and allows you to customize
the host and database name as well

    POSTGRES_HOST=host.docker.internal # Use this for a local database running on the host
    POSTGRES_USER=<yourname>
    POSTGRES_PASSWORD=<yourpassword>
    POSTGRES_DBNAME=dbt_container_skeleton # You will have to create this Postgres database

Lastly, open up a shell in the dbt container and try running the example dbt project

    inv dbt-shell
    dbt run

The container that runs mounts your local repository into the
container, so whenever you modify code on your host machine, it will
be immediately available in the container.

## Use

### Next steps for your project

After going through the setup exercises, you'll want to start
customizing this project for your dbt needs.  If you already have a
dbt project, you should be able to just copy your project into the
`dbt` directory.  One exception to this involves your dbt
`profiles.yml` file.  That file also needs to be placed in the `dbt`
directory.  However, you shouldn't commit this file to version control
if it contains any secrets.  Instead, all of the secrets in your
existing `profiles.yml` file should be replaced by environment
variables that get set via the `inv config` command mentioned above.
Examine the `dbt/profiles.yml` file in this project to how it is used.

If you need to add or modify the environment variables that get set in
the container, you only need to edit the `config_template.env` file.
This file too should not contain any secrets, as it merely lists out
the custom environment variables with some non-secret defaults. After
modifying this file, rerun `inv config` to set any secrets.

### A note about secrets

When you run `inv config` for the first time, a secret key is
generated and stored on your host machine at
`~/.dbt-container-skeleton`.  This is a key used to encrypt and
decrypt your secrets, which get stored in `.config.env` (also excluded
from version control).  If you lose the secret key, you will be unable
to decrypt this file and will have to rerun `inv config`.  This
ensures that secrets are not stored in plaintext on your host machine.

If you need to view the secrets in plaintext, you may do show with

    inv config-show


### Invoke

All of the `inv` commands are run via
[invoke](http://www.pyinvoke.org/) tasks defined in `tasks.py`.  To
see a list of available commads, run

    inv -l


### When to build?

Your host dbt folder is mounted within the container, so you do not
need to rebuild the container every time you change a file.  However,
whenever you need to modify a Python or dbt package, you'll need to run
`inv build` afterwards.

For example, if you needed to downgrade dbt to version `0.18.1`, You would
modify the `requirements.in` file and change the dbt line to `dbt==0.18.1`.  Then
compile the requirements to resolve package dependencies via

    inv requirements-compile

If all is successful (no package conflicts), rebuild the container with `inv build`.
