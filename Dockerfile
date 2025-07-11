ARG ARG_DOCKER_TAG=latest

FROM planolport/gdal_oracle:$ARG_DOCKER_TAG

LABEL maintainer="PlanolPort<planolport@portdebarcelona.cat>"

ARG CUSTOM_UID=65535
ARG USER_NAME=appuser
ARG base_path=/home/${USER_NAME}
# New ARG to track if Oracle is available
ARG ORACLE_AVAILABLE=1
ARG TEST_PYPI=0

RUN getent passwd ${USER_NAME} || useradd --create-home -u ${CUSTOM_UID} ${USER_NAME}

ENV PATH_DEVELOPER_MODE=/project
ENV PATH_BASE_PACKAGES=${PATH_DEVELOPER_MODE}

USER root

RUN mkdir ${PATH_DEVELOPER_MODE} && \
    chown -R $USER_NAME:root ${PATH_DEVELOPER_MODE} && \
    chmod -R u=rwx,g=rwx,o=rx ${PATH_DEVELOPER_MODE}

WORKDIR ${PATH_DEVELOPER_MODE}

COPY --chown=$USER_NAME:root ./requirements.txt ./requirements.txt

ENV USER_NAME=${USER_NAME}
USER $USER_NAME

RUN python -m venv --system-site-packages /home/$USER_NAME/venv \
    && . /home/$USER_NAME/venv/bin/activate

# Add local bin for $USER_NAME to PATH (for future pip installed scripts)
ENV PATH=/home/$USER_NAME/venv/bin:$PATH

RUN  pip install --upgrade pip -r requirements.txt --no-cache-dir

RUN if [ $TEST_PYPI = "1" ]; then \
            # Use Test PyPI if TEST_PYPI is set to 1
            pip config --site set global.extra-index-url https://test.pypi.org/simple; \
        fi

COPY --chown=$USER_NAME:root ./docs/ ./docs/
RUN chmod -R u=rwx,g=rwx,o=rx ./docs

RUN  pip install apb_extra_utils --no-cache-dir & \
          pip install apb_extra_osgeo_utils --no-cache-dir & \
          pip install apb_spatial_utils --no-cache-dir & \
          pip install apb_duckdb_utils --no-cache-dir;

RUN python -c  \
    "import duckdb; \
    duckdb.install_extension('sqlite'); \
    duckdb.install_extension('spatial'); \
    duckdb.install_extension('json'); \
    duckdb.install_extension('httpfs')"

# Install apb_pandas_utils with or without Oracle support based on Oracle availability
RUN if [ -d "$ORACLE_HOME/lib" ] && [ -f "$ORACLE_HOME/lib/libclntsh.so" ] && [ $ORACLE_AVAILABLE = "1" ]; then \
        echo "Installing apb_pandas_utils with Oracle support"; \
        pip install "apb_pandas_utils[oracle]" --no-cache-dir; \
    else \
        echo "Installing apb_pandas_utils without Oracle support"; \
        pip install apb_pandas_utils --no-cache-dir; \
    fi

CMD ["python"]
