# dbt container skeleton

todoc

## Initial Setup

### Prerequisites

* Download and install [docker community edition](https://www.docker.com/)

* Download and install [miniconda](https://conda.io/miniconda.html)

### Configuring your environment

Clone this repository to somewhere on your local development machine.

While all of core functionality of de-jobs runs in containers, we do
have to install a few python packages on the host to facilitate
various administrative tasks.  The best way to do this is to install
these packages in an isolated python environment provided by
miniconda.  Create and activate a de-jobs specific conda environment:

    conda create --name dbt-container-skeleton python=3.8
    conda activate dbt-container-skeleton

**Note**: when using miniconda, you will have to run `conda activate dbt-container-skeleton`
each time you start a new terminal session.

We use [invoke](http://www.pyinvoke.org/ to setup and control the environment
for developing, testing, and executing de-jobs.  The invoke file `tasks.py` makes use
of two other python packages: pip-tools and jinja2.  To install all of these packages
in the de-jobs environment, use pip:

    pip install -r host_requirements.txt
   pip install invoke pip-tools
