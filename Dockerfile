FROM python:3.8-slim

RUN apt-get update \
    && apt-get install -y \
        postgresql-client \
        libpq-dev \
        git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*


# dbt-runner app
ENV LC_ALL C.UTF-8
ENV LANG C.UTF-8
ENV PYTHONUNBUFFERED 1
ENV PYTHONPATH /dbt-runner
ENV DBT_PROFILES_DIR /dbt-runner/dbt
WORKDIR /dbt-runner

COPY requirements.txt requirements.txt
RUN pip install --upgrade pip
RUN pip install --ignore-installed -r requirements.txt && rm -rf /root/.cache

RUN mkdir -p /build_dbt_deps
COPY dbt/dbt_project.yml /build_dbt_deps/dbt_project.yml
COPY dbt/packages.yml /build_dbt_deps/packages.yml
RUN cd /build_dbt_deps \
    && dbt deps
