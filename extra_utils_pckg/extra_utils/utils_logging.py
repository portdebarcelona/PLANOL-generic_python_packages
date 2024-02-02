#  coding=utf-8
#
#  Author: Ernesto Arredondo Martinez (ernestone@gmail.com)
#  Created: 7/6/19 18:23
#  Last modified: 7/6/19 18:21
#  Copyright (c) 2019

import datetime
import logging
import logging.config
import os
from pathlib import Path
import tempfile
from operator import attrgetter

from . import get_root_logger, get_environ
from . import misc

LOG_HANDLER = "LOG"
REPORTS_HANDLER = 'REPORTS'
CONSOLE_HANDLER = 'console'
ENV_VAR_LOGS_DIR = "PYTHON_LOGS_DIR"


def get_base_logger(nom_base_log=None, level=None, parent_func=False):
    """
    Creates a logger for the context from where it is called with the logging level.

    Args:
        nom_base_log (str=None): Base name of the log. If not specified, it is obtained from the context where it is launched
        level (int=logging.INFO): Logger level (logging.DEBUG, logging.INFO, logging.WARNING, ...)
        parent_func (bool=False): If parent_func=True is indicated, then it returns the name of the context that calls the function

    Returns:
        logging.Logger: Logger instance for the function from where it is called
    """
    if not level:
        level = logging.INFO if get_environ() != 'dev' else logging.DEBUG

    skip_ctxt = 1
    if parent_func:
        skip_ctxt += 1

    if not nom_base_log:
        nom_base_log = misc.caller_name(skip_ctxt)

    root_logger = get_root_logger()
    a_logger = root_logger.getChild(nom_base_log)

    a_logger.setLevel(level)
    a_logger.propagate = True

    return a_logger


def get_file_logger(nom_base_log=None, level=None, dir_log=None, parent_func=False, sufix_date=True,
                    separate_reports=True, encoding='utf-8'):
    """
    Crea logger con FILEHANDLER (filehandlers si separate_reports a True)

    Si nombre del log (nom_base_log) no se especifica, se crea nombre de log con el nombre del contexto desde donde
    se llama y nombre de máquina si se puede obtener, y siempre la fecha actual

    Args:
        nom_base_log (str=None): Nombre base del log. Si no se especifica se obtiene del contexto donde se lanza
        level (int=logging.INFO): Nivel del logger (logging.DEBUG, logging.INFO, logging.WARNING, ...)
        dir_log (str, optional): Si se especifica, directorio donde guardar log
        parent_func (bool=False): Si se indica parent_func=True entonces devuelve el nombre del
                    contexto que llama a la funcion
        sufix_date (bool=True):
        separate_reports (bool=False): Si se indica separate_reports=True entonces se creará un file
                handler separado para el log de reports (logging.INFO)
        encoding (str='utf-8'): Encoding del fichero de log
    Returns:
        logging.logger: Instancia de logger para la funcion desde donde se llama
    """
    if not nom_base_log:
        nom_base_log = misc.caller_name(1 if not parent_func else 2)
    a_logger = get_base_logger(nom_base_log, level)

    if not a_logger.handlers:
        if not dir_log:
            dir_log = logs_dir(True)
        else:
            misc.create_dir(dir_log)

        sub_parts_nom = []
        if misc.machine_apb():
            sub_parts_nom.append(misc.machine_name())
        sub_parts_nom.append(nom_base_log)
        if sufix_date:
            sub_parts_nom.append(datetime.datetime.today().strftime('%Y%m%d_%H%M%S'))

        path_base_log = os.path.normpath(os.path.join(dir_log, "-".join(sub_parts_nom)))

        config_file_handlers = {
            handler.name: handler for handler in root_handlers()
            if handler.name != CONSOLE_HANDLER
        }

        def add_config_file_handler(handler, level_handler=None, sufix_handler=False):
            """
            Add handler to logger
            Args:
                handler (logging.Handler):
                level_handler (int, optional): If not specified, handler.level is used
                sufix_handler (bool=False): If True, handler.name is added to path_log
            """
            sufix_level = ""
            if sufix_handler:
                sufix_level = ".{}".format(handler.name.upper())

            path_log = ".".join(["{}{}".format(path_base_log, sufix_level),
                                 "log"])

            a_file_handler = logging.FileHandler(path_log, mode="w", encoding=encoding, delay=True)

            a_file_handler.setLevel(handler.level if not level_handler else level_handler)
            for flt in handler.filters:
                a_file_handler.addFilter(flt)
            a_frm = handler.formatter
            if a_frm:
                a_file_handler.setFormatter(a_frm)

            a_logger.addHandler(a_file_handler)

        if separate_reports and a_logger.level <= logging.INFO:
            if report_handler := config_file_handlers.get(REPORTS_HANDLER):
                add_config_file_handler(report_handler, sufix_handler=True)

        add_config_file_handler(config_file_handlers.get(LOG_HANDLER), level)

        root_logger = get_root_logger()
        root_level = root_logger.level
        root_logger.setLevel(logging.INFO)
        root_logger.info(f"Path prefix logs for FILE_LOGGER {nom_base_log}: '{path_base_log}'")
        root_logger.setLevel(root_level)

    return a_logger


def get_handler_for_level(level):
    """
    Devuelve el handler del logger root que se corresponde con el level de logging indicado

    Args:
        level (int): logging level

    Returns:
        logging.handler

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
        create (bool=False): Si TRUE y el directorio NO existe entonces se intentará crear

    Returns:
        str: Retorna path con el directorio de LOGS
    """
    path_logs_dir = os.getenv(ENV_VAR_LOGS_DIR, "").strip()

    if path_logs_dir and create and not misc.create_dir(path_logs_dir):
        get_root_logger().warning(
            "No se ha podido usar el directorio de logs '{}'"
            " indicado en la variable de entorno {}".format(path_logs_dir,
                                                            ENV_VAR_LOGS_DIR))
        path_logs_dir = None

    if not path_logs_dir or not misc.is_dir_writable(path_logs_dir):
        dir_base_logs = os.path.normpath(os.getenv("USERPROFILE", Path.home()))

        if not misc.is_path_exists_or_creatable(dir_base_logs):
            dir_base_logs = tempfile.gettempdir()

        dir_base_logs = os.path.join(dir_base_logs, "PYTHON_LOGS")
        if misc.get_environ() == "prod":
            path_logs_dir = os.path.join(dir_base_logs, "PROD")
        else:
            path_logs_dir = os.path.join(dir_base_logs, "dev")
        get_root_logger().warning(f'Usado por defecto el directorio de logs para el USERPROFILE: "{path_logs_dir}"')

        if create:
            misc.create_dir(path_logs_dir)

    return path_logs_dir


def logger_path_logs(a_logger=None, if_exist=True):
    """
    Returns the file paths where a_logger file handlers put his entries

    Args:
        a_logger (logging.Logger=None): default is root logger
        if_exist (bool=True): Returns the path if the file exists

    Returns:
        list
    """
    if a_logger is None:
        a_logger = get_root_logger()

    path_logs = []

    for fn in [hdlr.baseFilename
               for hdlr in a_logger.handlers if hasattr(hdlr, "baseFilename")]:
        if not if_exist or os.path.exists(fn):
            path_logs.append(fn)

    return path_logs


def filter_maker(level):
    """
    Returns a filter for logging handlers
    Args:
        level (str|int): logging level

    Returns:
        filter
    """
    if isinstance(level, str):
        level = getattr(logging, level)

    def filter(record):
        return record.levelno <= level

    return filter
