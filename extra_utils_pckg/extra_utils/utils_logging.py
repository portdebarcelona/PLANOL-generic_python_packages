#  coding=utf-8
#
#  Author: Ernesto Arredondo Martinez (ernestone@gmail.com)
#  Created: 7/6/19 18:23
#  Last modified: 7/6/19 18:21
#  Copyright (c) 2019

from __future__ import print_function, division, absolute_import

import datetime
import logging
import logging.config
import os
import tempfile
from operator import attrgetter

from . import get_root_logger
from . import misc


def get_file_logger(nom_base_log=None, level=None, dir_log=None, parent_func=False, sufix_date=True):
    """
    Crea logger para el contexto desde donde se llama con el nivel de logging.

    Si path del log (path_log) no se especifica, se crea nombre de log con el nombre del contexto desde donde se llama
    más el nombre del nivel


    Args:
        level {int, optional} (default=logging.INFO): Nivel del logger (logging.DEBUG, logging.INFO,
                                                    logging.WARNING, ...)
        path_log {str, optional}: Si se especifica, path fichero valido donde guardar log
        parent_func {bool, optional} (default=False): Si se indica parent_func=True entonces devuelve el nombre del
                                 contexto que llama a la funcion
        sufix_date {bool, optional} (default=True):
    Returns:
        {logging.logger}: Instancia de logger para la funcion desde donde se llama

    """
    root_logger = get_root_logger()
    if not level:
        level = root_logger.level

    skip_ctxt = 1
    if parent_func:
        skip_ctxt += 1

    if not nom_base_log:
        nom_base_log = misc.caller_name(skip_ctxt)

    a_logger = root_logger.getChild(nom_base_log)
    if not a_logger.handlers:
        if not dir_log:
            dir_log = logs_dir(True)
        else:
            misc.create_dir(dir_log)

        sub_parts_nom = []
        nom_pc = os.getenv("COMPUTERNAME")
        if nom_pc:
            sub_parts_nom.append(nom_pc)
        sub_parts_nom.append(nom_base_log)
        if sufix_date:
            sub_parts_nom.append(datetime.datetime.today().strftime('%Y%m%d_%H%M%S'))

        path_base_log = os.path.normpath(os.path.join(dir_log, "-".join(sub_parts_nom)))

        hdlrs = [h for h in root_handlers() if h.level >= level]
        sufix_hdlr = (len(hdlrs) > 1)
        sufix_level = ""
        for hdlr in hdlrs:
            if sufix_hdlr:
                sufix_level = ".{}".format(hdlr.name.upper())

            path_log = ".".join(["{}{}".format(path_base_log, sufix_level),
                                 "log"])

            a_file_handler = logging.FileHandler(path_log, mode="w", encoding="cp1252", delay=True)

            a_file_handler.setLevel(hdlr.level)
            a_frm = hdlr.formatter
            if a_frm:
                a_file_handler.setFormatter(a_frm)

            a_logger.addHandler(a_file_handler)

        a_logger.setLevel(level)
        a_logger.propagate = True

        root_logger.info("Path LOG base {}: {}".format(
            nom_base_log.upper(),
            path_base_log))

    return a_logger


def get_handler_for_level(level):
    """
    Devuelve el handler del logger root que se corresponde con el level de logging indicado

    Args:
        level {int}: logging level

    Returns:
        {logging.handler}

    """
    for hdl in root_handlers():
        if hdl.level <= level:
            return hdl


def root_handlers(desc=True):
    """
    Devuelve los handlers definidos en el logger root

    Returns:

    """
    rl = get_root_logger()
    sort_hdlrs = sorted(rl.handlers, key=attrgetter("level"), reverse=desc)

    return sort_hdlrs


def logs_dir(create=False):
    """
    Devuelve el directorio donde se guardarán los LOGS a partir de la variable de entorno "PYTHON_LOGS_DIR".
    Si no está informada devolverá el directorio de logs respecto al entorno de trabajo (misc.get_entorn())
        Entorno 'dev':  %USERPROFILE%/PYTHON_LOGS/dev
                'prod': %USERPROFILE%/PYTHON_LOGS/PROD

    Si el usuario no puede acceder a dichos directorios, se devolverá el directorio temporal de usuario
        %USERPROFILE%/AppData/Local/Temp/PYTHON_LOGS

    Args:
        create {bool:optional(default=False)}: Si TRUE y el directorio NO existe entonces se intentará crear

    Returns:
        str: Retorna path con el directorio de LOGS
    """
    _env_var_logs_dir_ = "PYTHON_LOGS_DIR"
    logs_dir = os.getenv(_env_var_logs_dir_, "").strip()

    if logs_dir and create and not misc.create_dir(logs_dir):
        print("!AVISO! - No se ha podido usar el directorio de logs '{}'"
              " indicado en la variable de entorno {}".format(logs_dir,
                                                              _env_var_logs_dir_))
        logs_dir = None

    if not logs_dir or not misc.is_dir_writable(logs_dir):
        dir_base_logs = os.path.normpath(os.getenv("USERPROFILE"))

        if not misc.is_path_exists_or_creatable(dir_base_logs):
            dir_base_logs = tempfile.gettempdir()

        dir_base_logs = os.path.join(dir_base_logs, "PYTHON_LOGS")
        if misc.get_environ() == "prod":
            logs_dir = os.path.join(dir_base_logs, "PROD")
        else:
            logs_dir = os.path.join(dir_base_logs, "dev")

        if create:
            misc.create_dir(logs_dir)

    return logs_dir
