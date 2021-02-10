#  coding=utf-8
#
#  Author: Ernesto Arredondo Martinez (ernestone@gmail.com)
#  Created: 7/6/19 18:23
#  Last modified: 7/6/19 18:21
#  Copyright (c) 2019

from __future__ import print_function, division, absolute_import

import calendar
import csv
import datetime
import errno
import inspect
import locale
import os
import subprocess
import sys
from calendar import different_locale
from collections import OrderedDict, namedtuple
from math import isnan
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

import jellyfish


def caller_name(skip=2):
    """Get a name of a caller in the format module.class.method

       `skip` specifies how many levels of stack to skip while getting caller
       name. skip=1 means "who calls me", skip=2 "who calls my caller" etc.

       An empty string is returned if skipped levels exceed stack height
    """

    def stack_(frame):
        framelist = []
        while frame:
            framelist.append(frame)
            frame = frame.f_back
        return framelist

    stack = stack_(sys._getframe(1))
    start = 0 + skip
    if len(stack) < start + 1:
        return ''
    parentframe = stack[start]

    name = []
    module = inspect.getmodule(parentframe)
    # `modname` can be None when frame is executed directly in console
    if module and module.__name__ != "__main__":
        name.append(module.__name__)
    # detect classname
    if 'self' in parentframe.f_locals:
        # I don't know any way to detect call from the object method
        # XXX: there seems to be no way to detect static method call - it will
        #      be just a function call
        name.append(parentframe.f_locals['self'].__class__.__name__)
    codename = parentframe.f_code.co_name
    if codename != '<module>':  # top level usually
        name.append(codename)  # function or a method
    del parentframe

    return ".".join(name)


def get_environ():
    """
    Devuelve el entorno de trabajo a partir de la environment variable DEV_ENVIRON.
    Si no está definida por defecto devuelve 'dev'

    Returns:
        str: El nombre del entorno 'dev' o 'prod'
    """
    return os.getenv("DEV_ENVIRON", "dev").lower()


def create_dir(a_dir):
    """
    Crea directorio devolviendo TRUE o FALSE según haya ido. Si ya existe devuelve TRUE

    Args:
        a_dir {str}: path del directorio a crear

    Returns:
        bool: Retorna TRUE si lo ha podido crear o ya existía y FALSE si no

    """
    ok = False
    if os.path.exists(a_dir):
        ok = True
    else:
        try:
            os.makedirs(a_dir)
            ok = True
        except:
            print("ATENCIÓ!! - No se ha podido crear el directorio", a_dir)

    return ok


def remove_content_dir(a_dir):
    """
    Borra ficheros y subdirectorios de directorio

    Args:
        a_dir {str}: path del directorio a crear

    Returns:
        num_elems_removed (int), num_elems_dir (int)
    """
    num_elems_removed = 0
    num_elems_dir = 0
    for de in os.scandir(a_dir):
        if de.is_dir():
            n_rem_subdir, n_subdir = remove_content_dir(de.path)
            num_elems_dir += n_subdir
            num_elems_removed += n_rem_subdir
            try:
                os.rmdir(de.path)
            except:
                pass
        else:
            num_elems_dir += 1
            try:
                os.unlink(de.path)
                num_elems_removed += 1
            except:
                pass

    return num_elems_removed, num_elems_dir


# Sadly, Python fails to provide the following magic number for us.
ERROR_INVALID_NAME = 123
'''
Windows-specific error code indicating an invalid pathname.

See Also
----------
https://msdn.microsoft.com/en-us/library/windows/desktop/ms681382%28v=vs.85%29.aspx
    Official listing of all such codes.
'''


def is_pathname_valid(pathname):
    '''
    `True` if the passed pathname is a valid pathname for the current OS;
    `False` otherwise.
    '''
    # If this pathname is either not a string or is but is empty, this pathname
    # is invalid.
    try:
        if not isinstance(pathname, str) or not pathname:
            return False

        # Strip this pathname's Windows-specific drive specifier (e.g., `C:\`)
        # if any. Since Windows prohibits path components from containing `:`
        # characters, failing to strip this `:`-suffixed prefix would
        # erroneously invalidate all valid absolute Windows pathnames.
        _, pathname = os.path.splitdrive(pathname)

        # Directory guaranteed to exist. If the current OS is Windows, this is
        # the drive to which Windows was installed (e.g., the "%HOMEDRIVE%"
        # environment variable); else, the typical root directory.
        root_dirname = os.environ.get('HOMEDRIVE', 'C:') \
            if sys.platform == 'win32' else os.path.sep
        assert os.path.isdir(root_dirname)  # ...Murphy and her ironclad Law

        # Append a path separator to this directory if needed.
        root_dirname = root_dirname.rstrip(os.path.sep) + os.path.sep

        # Test whether each path component split from this pathname is valid or
        # not, ignoring non-existent and non-readable path components.
        for pathname_part in pathname.split(os.path.sep):
            try:
                os.lstat(root_dirname + pathname_part)
            # If an OS-specific exception is raised, its error code
            # indicates whether this pathname is valid or not. Unless this
            # is the case, this exception implies an ignorable kernel or
            # filesystem complaint (e.g., path not found or inaccessible).
            #
            # Only the following exceptions indicate invalid pathnames:
            #
            # * Instances of the Windows-specific "WindowsError" class
            #   defining the "winerror" attribute whose value is
            #   "ERROR_INVALID_NAME". Under Windows, "winerror" is more
            #   fine-grained and hence useful than the generic "errno"
            #   attribute. When a too-long pathname is passed, for example,
            #   "errno" is "ENOENT" (i.e., no such file or directory) rather
            #   than "ENAMETOOLONG" (i.e., file name too long).
            # * Instances of the cross-platform "OSError" class defining the
            #   generic "errno" attribute whose value is either:
            #   * Under most POSIX-compatible OSes, "ENAMETOOLONG".
            #   * Under some edge-case OSes (e.g., SunOS, *BSD), "ERANGE".
            except OSError as exc:
                if hasattr(exc, 'winerror'):
                    if exc.winerror == ERROR_INVALID_NAME:
                        return False
                elif exc.errno in {errno.ENAMETOOLONG, errno.ERANGE}:
                    return False
    # If a "TypeError" exception was raised, it almost certainly has the
    # error message "embedded NUL character" indicating an invalid pathname.
    except TypeError as exc:
        return False
    # If no exception was raised, all path components and hence this
    # pathname itself are valid. (Praise be to the curmudgeonly python.)
    else:
        return True
    # If any other exception was raised, this is an unrelated fatal issue
    # (e.g., a bug). Permit this exception to unwind the call stack.
    #
    # Did we mention this should be shipped with Python already?


def is_dir_writable(dirname):
    '''
    `True` if the current user has sufficient permissions to create **siblings**
    (i.e., arbitrary files in the parent directory) of the passed pathname;
    `False` otherwise.
    '''
    try:
        a_tmp = os.path.join(dirname, "temp.tmp")
        with open(a_tmp, 'w+b'):
            pass

        try:
            os.remove(a_tmp)
        except:
            pass

        return True

    # While the exact type of exception raised by the above function depends on
    # the current version of the Python interpreter, all such types subclass the
    # following exception superclass.
    except:
        return False


def is_path_exists_or_creatable(pathname):
    '''
    `True` if the passed pathname is a valid pathname on the current OS _and_
    either currently exists or is hypothetically creatable in a cross-platform
    manner optimized for POSIX-unfriendly filesystems; `False` otherwise.

    This function is guaranteed to _never_ raise exceptions.
    '''
    try:
        # To prevent "os" module calls from raising undesirable exceptions on
        # invalid pathnames, is_pathname_valid() is explicitly called first.
        return is_pathname_valid(pathname) and (
                os.path.exists(pathname) or is_dir_writable(os.path.dirname(pathname)))
    # Report failure on non-fatal filesystem complaints (e.g., connection
    # timeouts, permissions issues) implying this path to be inaccessible. All
    # other exceptions are unrelated fatal issues and should not be caught here.
    except OSError:
        return False


def get_matching_val(search_val, matching_vals):
    """
    Retorna el valor que se asimila a los valores a comparar (matching_vals) respecto al valor propuesto
    (prop_val).

    Args:
        search_val (str): Valor propuesto para comparar
        mathing_vals (list(str)): Lista de valores a comparar

    Returns:
        match_val (str), fact_jaro_winkler (float)
    """
    jaro_results = jaro_winkler(search_val, matching_vals)
    fact_jaro = next(iter(jaro_results), None)

    return jaro_results.get(fact_jaro), fact_jaro


def levenshtein_distance(search_val, matching_vals):
    """

    Args:
        search_val:
        matching_vals:

    Returns:

    """
    ord_vals = OrderedDict()
    distances = {}
    for match_val in matching_vals:
        fact = jellyfish.levenshtein_distance(search_val, match_val)
        vals_fact = distances.get(fact, list())
        distances[fact] = vals_fact + [match_val]

    for fact in sorted(distances):
        ord_vals[fact] = distances.get(fact, [])

    return ord_vals


def jaro_winkler(search_val, matching_vals):
    """

    Args:
        search_val:
        matching_vals:

    Returns:

    """
    ord_vals = OrderedDict()
    matchings = {jellyfish.jaro_winkler(search_val, match_val): match_val
                 for match_val in matching_vals}
    for fact in sorted(matchings, reverse=True):
        if fact != 0:
            ord_vals[fact] = matchings[fact]

    return ord_vals


def call_command(command_prog, *args):
    """
    Llama comando shell sistema con los argumentos indicados

    Returns:
        bool: True si OK

    """
    call_args = [command_prog]
    call_args.extend(args)
    ret = subprocess.check_call(call_args, shell=True)

    return (ret == 0)


def rounded_float(a_float, num_decs=9):
    """
    Formatea un float con el numero de decimales especificado
    Args:
        a_float:
        num_decs:

    Returns:
        str
    """
    return float(format(round(a_float, num_decs), ".{}f".format(num_decs)).rstrip('0').rstrip('.'))


class formatted_float(float):
    """
    Devuelve un float que se representa con un maximo de decimales (__num_decs__)
    """
    __num_decs__ = 9

    def __repr__(self):
        return str(rounded_float(self, self.__num_decs__))


def as_format_floats(obj):
    """
    Si encuentra un Float lo convierte a la clase 'formatted_float' para formatear su representación

    Args:
        obj: Cualquier objeto

    Returns:
        (obj, formatted_float)

    """
    if isinstance(obj, (float, formatted_float)):
        return formatted_float(obj)
    elif isinstance(obj, (dict, OrderedDict)):
        return obj.__class__((k, as_format_floats(v)) for k, v in obj.items())
    elif isinstance(obj, (list, tuple)):
        return obj.__class__(as_format_floats(v) for v in obj)
    return obj


def nums_from_str(a_string, nan=False):
    """
    Retorna lista de numeros en el texto pasado

    Args:
        a_string (str):
        nan (bool=FAlse): por defecto no trata los NaN como numeros

    Returns:
        list
    """
    l_nums = []

    for s in a_string.strip().split():
        try:
            l_nums.append(int(s))
        except ValueError:
            try:
                fl = float(s)
                if nan or not isnan(fl):
                    l_nums.append(fl)
            except ValueError:
                pass

    return l_nums


def first_num_from_str(a_string, nan=False):
    """
    Retorna primer numero encontrado del texto pasado

    Args:
        a_string (str):
        nan (bool=FAlse): por defecto no trata los NaN como numeros

    Returns:
        int OR float
    """
    return next(iter(nums_from_str(a_string, nan=nan)), None)


def dates_from_str(str, formats=None, seps=None, ret_extra_data=False):
    """
    Retorna dict de fechas disponibles con el texto pasado segun formatos indicados

    Args:
        str (str):
        formats (list=None): por defecto ['%Y%m%d', '%Y/%m/%d', '%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d']
        seps (list=None): por defecto [None, '.', ',']
        ret_extra_data (bool=False): si True retorna tuple con fecha + part_str_src + format utilizado

    Returns:
        list
    """
    l_fechas = list()

    if not formats:
        formats = ['%Y%m%d', '%Y/%m/%d', '%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d']

    if not seps:
        seps = [None, '.', ',']

    str_parts = [s.strip() for sep in seps for s in str.split(sep)]

    for format in formats:
        for str_part in str_parts:
            try:
                val = datetime.datetime.strptime(str_part, format)
                if ret_extra_data:
                    val = (val, str_part, format)
                l_fechas.append(val)
            except Exception:
                pass

    return l_fechas


def pretty_text(txt):
    """
    Coge texto y lo capitaliza y quita carácteres por espacios
    Args:
        txt (str):

    Returns:
        str
    """
    return txt.replace("_", " ").replace("-", " ").capitalize()


def zip_files(zip_path, *file_paths):
    """
    Comprime los ficheros indicados con :file_paths en un fichero zip (:zip_path)

    Args:
        zip_path:
        *file_paths:
    Returns:
        zip_path (str)
    """
    with ZipFile(zip_path, "w", compression=ZIP_DEFLATED, allowZip64=True) as my_zip:
        for file_path in file_paths:
            my_zip.write(file_path, arcname=os.path.basename(file_path))

    return zip_path


def zip_files_dir(dir_path, remove_files=False, *exts_files):
    """
    Comprime los ficheros de una carpeta indicada. Se pueden indicar qué tipo de ficheros se quiere que comprima

    Args:
        dir_path:
        remove_files:
        *exts_files: extensiones de fichero SIN el punto

    Returns:
        ok (bool)
    """
    exts = [".{}".format(ext.lower()) for ext in exts_files]
    for zip_path, file_path in (("{}.zip".format(os.path.splitext(de.path)[0]), de.path)
                                for de in os.scandir(dir_path)):
        if not exts or (os.extsep in file_path and os.path.splitext(file_path)[1].lower() in exts):
            print("Comprimiendo fichero '{}' en el zip '{}'".format(file_path, zip_path))
            zip_files(zip_path, file_path)

            if remove_files and not os.path.samefile(zip_path, file_path):
                os.remove(file_path)

    return True


def split_ext_file(path_file):
    """
    Devuelve el nombre del fichero partido entre la primera parte antes del separador "." y lo demás
    Args:
        path_file:
    Returns:
        base_file (str), ext_file (str)
    """
    parts_file = os.path.basename(path_file).split(".")
    base_file = parts_file[0]
    ext_file = ".".join(parts_file[1:])

    return base_file, ext_file


FILE_RUN_LOG = "last_run.log"
DATE_RUN_LOG_FRMT = "%Y%m%d"


def last_run_on_dir(dir_base):
    """
    Retorna la fecha de ultima ejecucion de proceso generacion en directorio de repositorio
    Args:
        dir_base (str):

    Returns:
        date_last_run (datetime): Si no encuentra devuelve None
    """
    log_last_run = os.path.join(dir_base, FILE_RUN_LOG)
    dt_last_run = None
    if os.path.exists(log_last_run):
        with open(log_last_run) as fr:
            dt_last_run = datetime.datetime.strptime(fr.read(), DATE_RUN_LOG_FRMT)

    return dt_last_run


def save_last_run_on_dir(dir_base, date_run=None):
    """
    Graba la fecha de ultima ejecucion de proceso generacion en directorio de repositorio

    Args:
        dir_base (str):
        date_run (datetime=None): Si no se informa cogerá la fecha de hoy
    """
    log_last_run = os.path.join(dir_base, FILE_RUN_LOG)
    if not date_run:
        date_run = datetime.date.today()
    with open(log_last_run, "w+") as fw:
        fw.write(date_run.strftime(DATE_RUN_LOG_FRMT))


def month_name(num_month, code_alias_locale="es_cu"):
    """
    Retorna numero de mes en el locale espcificado. Por defecto castellano

    Args:
        num_month (int):
        year (int=datetime.date.today().year):
        code_alias_locale (str='es_es'):

    Returns:
        str
    """
    with different_locale(locale.locale_alias.get(code_alias_locale)):
        return pretty_text(calendar.month_name[num_month])


def rows_csv(a_path_csv, header=True, sep=';', encoding="utf8"):
    """
    Itera como namedtuples indexado por valores primera fila (si header=True, si no num. columna) las filas del CSV pasado por parametro a_path_csv

    Args:
        a_path_csv (str):
        header (bool=True):
        sep (str=';'): por defecto cogerá el separador que por defecto usa csv.reader
        encoding (str="utf8"):
    Yields:
        dict OR list
    """
    with open(a_path_csv, encoding=encoding) as a_file:
        csv_rdr=csv.reader(a_file, delimiter=sep)
        nt_row = None
        for row in csv_rdr:
            if not nt_row:
                if header:
                    nt_row = namedtuple("row_csv",
                                        [v.replace(" ", "_").upper() for v in row])
                    continue
                else:
                    nt_row = namedtuple("row_csv",
                                        ["C{}".format(c) for c in range(1, len(row) + 1)])

            yield nt_row(*row)


if __name__ == '__main__':
    import fire
    fire.Fire()
