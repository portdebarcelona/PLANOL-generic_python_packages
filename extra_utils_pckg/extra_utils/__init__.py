#   coding=utf-8
#  #
#   Author: ernst
#   File: __init__.py
#   Created: 29/01/2020, 19:11
#   Last modified: 29/01/2020, 19:10
#   Copyright (c) 2020
"""
.. include:: ../README.md
"""


__path__ = __import__('pkgutil').extend_path(__path__, __name__)

# EAM - Para evitar error ddl al usar OSGEO.GDAL se asegura import antes de hacer uso del modulo logging
try:
    __import__("osgeo")
except:
    pass

import logging
import logging.config
import os
import yaml
from .misc import get_environ


__conf_logging__ = os.path.join(os.path.dirname(__file__), "logging.conf.yml")
__nom_env_config_logging__ = "LOGGING_CONF_PATH"

if __nom_env_config_logging__ in os.environ:
    if os.getenv(__nom_env_config_logging__).strip():
        __conf_logging__ = os.getenv(__nom_env_config_logging__).strip()


def set_logging_config(log_config_path):
    """
    Configura el logging de sesión

    Args:
        log_name_file {str, optional}: Si asignado entonces carga la configuracion de logging de ahí.
                Defecto "logging.conf.yml"
        log_level {obj, optional}: Nivel de logging (logging.DEBUG, logging.INFO, logging.WARNING,...). Por defecto INFO

    Returns:
        str: Retorna el path del fichero cargado

    """
    info_msg = None
    if os.path.exists(log_config_path):
        with open(log_config_path, 'rt') as f:
            config = yaml.safe_load(f.read())
        logging.config.dictConfig(config)
        info_msg = "Cargado fichero de configuracion de LOGGING '{}'".format(log_config_path)
    else:
        logging.basicConfig()

    if get_environ() == "prod":
        set_level_logging(logging.INFO)

    root_logger = get_root_logger()
    if info_msg:
        root_logger.info(info_msg)


def get_root_logger():
    """
    Devuelve el logger base del modulo logging

    Returns:
        logging.logger
    """
    return logging.getLogger()


def set_level_logging(a_logging_lvl=logging.INFO):
    """
    Asigna nivel de logging por el que se mostrarán mensajes

    Args:
        a_logging_lvl: (logging.DEBUG, logging.INFO, logging.WARNING, ...)

    Returns:
    """
    root_logger = get_root_logger()
    root_logger.setLevel(a_logging_lvl)


set_logging_config(__conf_logging__)
