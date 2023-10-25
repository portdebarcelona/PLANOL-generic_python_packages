FROM ghcr.io/osgeo/gdal:ubuntu-small-3.6.3 AS runtime

ARG oracle_client_version=19.18
ARG path_oracle_client=./config/oracle/
ARG CUSTOM_UID=65535

RUN useradd --create-home -u ${CUSTOM_UID} appuser

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
    && apt-get install -yq --no-install-recommends pip alien libaio1 locales locales-all tzdata \
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

LABEL maintainer="PlanolPort<planolport@portdebarcelona.cat>"

RUN mkdir /project && \
    chown -R appuser:root /project && \
    chmod -R u=rwx,g=rwx,o=rx /project
WORKDIR /project

COPY --chown=appuser:root ./docs/ ./docs/
RUN chmod -R u=rwx,g=rwx,o=rx ./docs

COPY --chown=appuser:root ./requirements.txt ./requirements.txt
RUN pip install --upgrade pip -r requirements.txt --no-cache-dir

ENV PATH_DEVELOPER_MODE=/project
COPY --chown=appuser:root ./extra_utils_pckg/ ./extra_utils_pckg/
RUN pip install --editable extra_utils_pckg --no-cache-dir

COPY --chown=appuser:root ./extra_osgeo_utils_pckg/ ./extra_osgeo_utils_pckg/
RUN pip install --editable extra_osgeo_utils_pckg --no-cache-dir

COPY --chown=appuser:root ./spatial_utils_pckg/ ./spatial_utils_pckg/
RUN pip install --editable spatial_utils_pckg --no-cache-dir

COPY --chown=appuser:root ./cx_oracle_spatial_pckg/ ./cx_oracle_spatial_pckg/
# Set env var for package python cx_oracle_spatial
ENV PATH_INSTANT_CLIENT_ORACLE=$ORACLE_HOME
RUN pip install --editable cx_oracle_spatial_pckg --no-cache-dir

COPY --chown=appuser:root ./pandas_utils_pckg/ ./pandas_utils_pckg/
RUN pip install --editable pandas_utils_pckg --no-cache-dir

# Add local bin for appuser to PATH (for future pip installed scripts)
ENV PATH=/home/appuser/.local/bin:$PATH
USER appuser

CMD ["python"]
