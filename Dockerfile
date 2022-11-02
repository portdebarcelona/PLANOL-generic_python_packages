FROM continuumio/miniconda3:latest as build

LABEL maintainer="PlanolPort<planolport@portdebarcelona.cat>"

ENV TZ=Europe/Madrid

ENV PYTHONUNBUFFERED 1
ENV LANG C.UTF-8

RUN mkdir /project
WORKDIR /project

COPY environment.yml .
RUN conda env create -f environment.yml

COPY requirements.txt .
RUN conda run -n python_packages pip install --requirement requirements.txt --no-cache-dir

COPY ./config/unix/post_install_python.sh .
RUN chmod u=rwx post_install_python.sh && conda run -n python_packages ./post_install_python.sh

# Install conda-pack:
RUN conda install -c conda-forge conda-pack

# Use conda-pack to create a standalone enviornment
# in /venv:
RUN conda-pack -n python_packages -o /tmp/env.tar && \
  mkdir /venv && cd /venv && tar xf /tmp/env.tar && \
  rm /tmp/env.tar

# We've put venv in same path it'll be in final image,
# so now fix up paths:
RUN /venv/bin/conda-unpack


# The runtime-stage image; we can use Debian as the
# base image since the Conda env also includes Python
# for us.
FROM debian:buster AS runtime

ARG oracle_client_version=19.15
ARG path_oracle_client=./config/oracle/

RUN useradd --create-home appuser

# Instant client
COPY $path_oracle_client /tmp/oracle
ENV ORACLE_HOME=/usr/lib/oracle/${oracle_client_version}/client64
ENV LD_LIBRARY_PATH=$ORACLE_HOME/lib
ENV TNS_ADMIN=/usr/lib/oracle/${oracle_client_version}/client64/tns

RUN mkdir --parents $ORACLE_HOME && \
    chmod -R o=rx ${ORACLE_HOME} && \
    mkdir ${TNS_ADMIN}

RUN apt-get update \
    && apt-get install -yq --no-install-recommends alien libaio1 \
    && cd /tmp/oracle \
    && for rpm in ./*.rpm; do alien -i $rpm; done \
    && ln -s ${ORACLE_HOME} ${ORACLE_HOME}/include \
    # Remove alien and unnecesary deps.
    && apt-get -yq remove --auto-remove --purge alien \
    && rm -rf /tmp/oracle \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /app \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime \
    && echo $TZ > /etc/timezone

RUN mkdir /venv && \
    chmod -R o=rx /venv

# Copy /venv from the previous stage:
COPY --from=build /venv /venv
ENV VIRTUAL_ENV=/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

LABEL maintainer="PlanolPort<planolport@portdebarcelona.cat>"

ENV TZ=Europe/Madrid

RUN mkdir /project
RUN chown -R appuser /project
WORKDIR /project

ENV PATH_DEVELOPER_MODE=/project
COPY ./extra_utils_pckg/ ./extra_utils_pckg/
RUN pip install --editable extra_utils_pckg --no-cache-dir

COPY ./extra_osgeo_utils_pckg/ ./extra_osgeo_utils_pckg/
RUN pip install --editable extra_osgeo_utils_pckg --no-cache-dir

COPY ./spatial_utils_pckg/ ./spatial_utils_pckg/
RUN pip install --editable spatial_utils_pckg --no-cache-dir

COPY ./cx_oracle_spatial_pckg/ ./cx_oracle_spatial_pckg/
# Set env var for package python cx_oracle_spatial
ENV PATH_INSTANT_CLIENT_ORACLE=$ORACLE_HOME
RUN pip install --editable cx_oracle_spatial_pckg --no-cache-dir

COPY ./pandas_utils_pckg/ ./pandas_utils_pckg/
RUN pip install --editable pandas_utils_pckg --no-cache-dir

USER appuser

CMD ["python"]
