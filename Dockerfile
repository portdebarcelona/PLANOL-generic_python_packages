FROM ghcr.io/osgeo/gdal:ubuntu-small-3.8.5 AS runtime

LABEL maintainer="PlanolPort<planolport@portdebarcelona.cat>"

ARG oracle_client_version=19.18
ARG path_oracle_client=./config/oracle/
ARG CUSTOM_UID=65535
ARG USER_NAME=appuser
ARG base_path=/home/${USER_NAME}

RUN getent passwd ${USER_NAME} || useradd --create-home -u ${CUSTOM_UID} ${USER_NAME}

# Instant client
COPY $path_oracle_client /tmp/oracle
ENV ORACLE_HOME=/usr/lib/oracle/${oracle_client_version}/client64
ENV LD_LIBRARY_PATH=$ORACLE_HOME/lib
ENV TNS_ADMIN=/usr/lib/oracle/${oracle_client_version}/client64/tns
ENV TZ=Europe/Madrid

RUN mkdir --parents $ORACLE_HOME && \
    chmod -R o=rx ${ORACLE_HOME} && \
    mkdir ${TNS_ADMIN}

RUN export DEBIAN_FRONTEND=noninteractive \
    && apt-get update && apt-get upgrade -yq \
    && apt-get install -yq --no-install-recommends pip alien libaio1 locales locales-all tzdata nodejs npm \
    && cd /tmp/oracle \
    && for rpm in ./*.rpm; do alien -i --scripts $rpm; done \
    && ln -s ${ORACLE_HOME} ${ORACLE_HOME}/include \
    # Set timezone \
    && ln -fs /usr/share/zoneinfo/$TZ /etc/localtime \
    && dpkg-reconfigure --frontend noninteractive tzdata \
    && echo $TZ > /etc/timezone \
    # Remove alien and unnecesary deps.
    && apt-get -yq remove --auto-remove --purge alien \
    && rm -rf /tmp/oracle \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /app \
    && apt-get clean

ARG ARG_LANG=es_ES.UTF-8
ENV LANG=$ARG_LANG
ENV LANGUAGE=$ARG_LANG
ENV LC_ALL=$ARG_LANG
ENV PYTHONUNBUFFERED 1

ENV PATH_DEVELOPER_MODE=/project
ENV PATH_BASE_PACKAGES=${PATH_DEVELOPER_MODE}

RUN mkdir ${PATH_DEVELOPER_MODE} && \
    chown -R $USER_NAME:root ${PATH_DEVELOPER_MODE} && \
    chmod -R u=rwx,g=rwx,o=rx ${PATH_DEVELOPER_MODE}

WORKDIR ${PATH_DEVELOPER_MODE}

ENV USER_NAME=${USER_NAME}

USER $USER_NAME

# Add local bin for $USER_NAME to PATH (for future pip installed scripts)
ENV PATH=/home/$USER_NAME/.local/bin:$PATH

COPY --chown=$USER_NAME:root ./docs/ ./docs/
RUN chmod -R u=rwx,g=rwx,o=rx ./docs

COPY --chown=$USER_NAME:root ./requirements.txt ./requirements.txt
RUN pip install --upgrade pip -r requirements.txt --no-cache-dir

COPY --chown=$USER_NAME:root ./extra_utils_pckg/ ./extra_utils_pckg/
RUN pip install  --config-setting editable_mode=compat --no-build-isolation --editable extra_utils_pckg --no-cache-dir

COPY --chown=$USER_NAME:root ./extra_osgeo_utils_pckg/ ./extra_osgeo_utils_pckg/
RUN pip install  --config-setting editable_mode=compat --no-build-isolation --editable extra_osgeo_utils_pckg --no-cache-dir

COPY --chown=$USER_NAME:root ./spatial_utils_pckg/ ./spatial_utils_pckg/
RUN pip install  --config-setting editable_mode=compat --no-build-isolation --editable spatial_utils_pckg --no-cache-dir

COPY --chown=$USER_NAME:root ./cx_oracle_spatial_pckg/ ./cx_oracle_spatial_pckg/
# Set env var for package python cx_oracle_spatial
ENV PATH_INSTANT_CLIENT_ORACLE=$ORACLE_HOME
RUN pip install  --config-setting editable_mode=compat --no-build-isolation --editable cx_oracle_spatial_pckg --no-cache-dir

COPY --chown=$USER_NAME:root ./pandas_utils_pckg/ ./pandas_utils_pckg/
RUN pip install  --config-setting editable_mode=compat --no-build-isolation --editable pandas_utils_pckg --no-cache-dir

COPY --chown=$USER_NAME:root ./duckdb_utils_pckg/ ./duckdb_utils_pckg/
RUN pip install  --config-setting editable_mode=compat --no-build-isolation --editable duckdb_utils_pckg --no-cache-dir
# Set extra extensions perinstalled on duckdb
RUN python -c  \
    "import duckdb; \
    duckdb.install_extension('sqlite'); \
    duckdb.install_extension('spatial'); \
    duckdb.install_extension('json'); \
    duckdb.install_extension('httpfs')"

CMD ["python"]
