# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

#
#  FLOWDB
#  -----
#
#
#  This image is based on the official
#  PostgreSQL image, which is based
#  on the official Debian Stretch (9) image.
#

FROM postgres@sha256:38eb50ceaf0bfe82a9c768e5537a012b58bb4fff0b0e4242e79dea992520c30f


ARG POSTGIS_MAJOR=3
ENV POSTGIS_MAJOR=$POSTGIS_MAJOR
ARG POSTGIS_VERSION=3.0.1+dfsg-2.pgdg100+1
ARG PGROUTING_VERSION=3.0.0~rc1-1.pgdg100+1
ARG PG_MEDIAN_UTILS_VERSION=0.0.7
ARG OGR_FDW_VERSION=1.0.11-1.pgdg100+1
ENV POSTGIS_VERSION=$POSTGIS_VERSION
ENV POSTGRES_DB=flowdb
ARG POSTGRES_USER=flowdb
ENV POSTGRES_USER=$POSTGRES_USER
ENV LC_ALL=en_US.UTF-8
ENV LC_CTYPE=en_US.UTF-8
ENV TDS_FDW_VERSION=2.0.1


RUN apt-get update \
        && apt-get install -y --no-install-recommends \
        postgresql-$PG_MAJOR-postgis-$POSTGIS_MAJOR=$POSTGIS_VERSION  \
        postgresql-$PG_MAJOR-postgis-$POSTGIS_MAJOR-scripts=$POSTGIS_VERSION \
        postgresql-$PG_MAJOR-pgrouting=$PGROUTING_VERSION \
        postgresql-$PG_MAJOR-ogr-fdw=$OGR_FDW_VERSION \
        postgresql-server-dev-$PG_MAJOR=$PG_VERSION \
        postgis=$POSTGIS_VERSION \
        && rm -rf /var/lib/apt/lists/* \
        && apt-get purge -y --auto-remove

#
#  Setting up locale settings. This will
#  eventually fix encoding issues.
#
RUN apt-get update && apt-get install -y --no-install-recommends locales locales-all \
        && localedef -i en_US -c -f UTF-8 -A /usr/share/locale/locale.alias en_US.UTF-8 \
        && locale-gen && rm -rf /var/lib/apt/lists/*

#
#  INSTALLING DEPENDENCIES
#  -----------------------
#
#  In this section we install the dependencies
#  that the database will use when analysing
#  data.

#
# Install some useful extras & python dependencies
#
RUN apt-get update \
        && apt-get install -y --no-install-recommends \
        unzip curl make postgresql-plpython3-$PG_MAJOR \
        libaio1  \
        parallel nano vim python3-pip wget python3-setuptools\
        && apt purge -y --auto-remove \
        && rm -rf /var/lib/apt/lists/*

# add requirements for pg_admin debugging
ENV USE_PGXS=1
RUN apt-get update \
        && apt-get install -y --no-install-recommends libssl-dev \
        libkrb5-dev \ 
        build-essential \
        git \
        && git clone https://git.postgresql.org/git/pldebugger.git \
        && mv pldebugger /usr/local/src \
        && make -C /usr/local/src/pldebugger \
        && make -C /usr/local/src/pldebugger install \
        && apt-get remove -y libssl-dev \
        libkrb5-dev \
        build-essential \
        git \
        && apt purge -y --auto-remove \
        && rm -rf /var/lib/apt/lists/*

# TDS_FDW

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libsybdb5 freetds-dev freetds-common gnupg gcc wget && \
    wget https://github.com/tds-fdw/tds_fdw/archive/v${TDS_FDW_VERSION}.tar.gz && \
    tar -xvzf v${TDS_FDW_VERSION}.tar.gz && \
    rm v${TDS_FDW_VERSION}.tar.gz && \
    cd tds_fdw-${TDS_FDW_VERSION}/ && \
    make USE_PGXS=1 && \
    make USE_PGXS=1 install && \
    cd .. && rm -rf tds_fdw-${TDS_FDW_VERSION} && \
    apt-get remove -y gnupg gcc && \
    apt purge -y --auto-remove  &&\
    rm -rf /var/lib/apt/lists/*



#
#  CONFIGURATION
#  -------------
#
#  In this section packages installed in previous
#  steps are properly configured. That happens by
#  either modifying configuration files (*.config)
#  or by loading *.sh scripts that will gradually
#  do that.
#
RUN mkdir -p /docker-entrypoint-initdb.d

#
#  Let's now install the `flowdb-cli` program
#  and run its automatic configuration command.
#
#  pipenv uses the first pip and python found in the
#  PATH so we need to force the right python version
#  together with the appropriate headers, otherwise
#  psutil fails to install.
#
# We'll also install useful postgres extensions distributed via PGXN.
#
COPY ./flowdb/Pipfile* /tmp/
RUN apt-get update \
        && apt-get install -y --no-install-recommends python3-dev gcc m4 libxml2-dev libaio-dev  \
        && pip3 install pgxnclient \
        && pgxnclient install "pg_median_utils=$PG_MEDIAN_UTILS_VERSION" \
        && pip3 install pipenv \
        && PIPENV_PIPFILE=/tmp/Pipfile pipenv install --system --deploy --three \
        && apt-get remove -y python3-dev gcc m4 libxml2-dev libaio-dev \
        && apt purge -y --auto-remove \
        && rm -rf /var/lib/apt/lists/*

# Version Information
# Set the version & release date
ARG FLOWDB_VERSION=v1.7.2
ENV FLOWDB_VERSION=$FLOWDB_VERSION
ARG FLOWDB_RELEASE_DATE='3000-12-12'
ENV FLOWDB_RELEASE_DATE=$FLOWDB_RELEASE_DATE

# Default users

ENV FLOWMACHINE_FLOWDB_USER=flowmachine
ENV FLOWAPI_FLOWDB_USER=flowapi

# Default location table
ENV LOCATION_TABLE=infrastructure.cells

#
#  Copy file spinup build scripts to be execed.
#
COPY --chown=postgres ./flowdb/bin/build/* /docker-entrypoint-initdb.d/

#
#  Add local data to PostgreSQL data ingestion
#  directory. Files in that directory will be
#  ingested by PostgreSQL on build-time.
#
ADD --chown=postgres ./flowdb/data/* /docker-entrypoint-initdb.d/data/csv/
# Need to make postgres owner
RUN chown -R postgres /docker-entrypoint-initdb.d

EXPOSE 5432
