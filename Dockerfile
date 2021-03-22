FROM continuumio/miniconda3:latest
#FROM osgeo/gdal
ENV PYTHONUNBUFFERED 1
ENV LANG C.UTF-8

RUN mkdir /project
WORKDIR /project
COPY . /project

#CMD ["/bin/bash"]

RUN apt-get install libaio1

#RUN apt-get update -y \
#    && apt-get install -y --fix-missing --no-install-recommends python3-pip

# conda !NO funcionan los environments dentro!
RUN conda install --file environment.docker.yml

ENV PATH_DEVELOPER_MODE /project
RUN pip install --editable extra_utils_pckg
RUN pip install --editable osgeo_utils_pckg
RUN pip install --editable spatial_utils_pckg
RUN pip install --editable cx_oracle_spatial_pckg
RUN pip install --editable pandas_utils_pckg

RUN /project/config/unix/post_install_python.sh
