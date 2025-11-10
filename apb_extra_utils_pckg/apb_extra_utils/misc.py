#  coding=utf-8
#
#  Author: Ernesto Arredondo Martinez (ernestone@gmail.com)
#  Created: 7/6/19 18:23
#  Last modified: 7/6/19 18:21
#  Copyright (c) 2019
from __future__ import annotations

import calendar
import csv
import datetime
import errno
import inspect
import locale
import os
import re
import socket
import subprocess
import sys
from calendar import different_locale
from collections import OrderedDict
from math import isnan
from pathlib import Path
from tempfile import gettempdir
from typing import Any, Generator, Tuple
from urllib.request import build_opener
from zipfile import ZipFile, ZIP_DEFLATED

import jellyfish
from tqdm import tqdm


def download_and_unzip(url: str, extract_to: str = None, headers: list = None, remove_zip: bool = True):
    """

    Args:
        url (str):
        extract_to (str=None): if None, extract to current directory
        headers (list=None)
        remove_zip (bool=True):

    Returns:
        path_zip (str)
    """
    if zip_file_path := download_from_url(url, extract_to, headers):
        extract_to = unzip(zip_file_path, extract_to, remove_zip)

        return extract_to


def unzip(zip_file_path, extract_to=None, remove_zip=False):
    """
    Unzip file to extract_to directory

    Args:
        zip_file_path (str): Path to zip file
        extract_to: (str=None): if None, extract to zip's directory
        remove_zip: (bool=False): If True remove zip file after unzip

    Returns:
        extract_to (str)
    """
    with ZipFile(zip_file_path, 'r') as zipfile:
        if not extract_to:
            extract_to = os.path.join(
                os.path.dirname(zip_file_path),
                os.path.splitext(os.path.basename(zip_file_path))[0]
            )

        desc = f"Extracting {zip_file_path} to {extract_to}"
        if not sys.stdout:
            print(f'{desc}...')
            gen_members = zipfile.infolist()
        else:
            gen_members = tqdm(zipfile.infolist(), desc=desc)

        for member in gen_members:
            zipfile.extract(member, extract_to)
    if remove_zip:
        os.remove(zip_file_path)
    return extract_to


def download_from_url(url: str, extract_to: str = None, headers: list[str] = None) -> str:
    """

    Args:
        url (str): Url to download
        extract_to (str=None): Directory to save file. Default temporary directory
        headers (list=None)

    Returns:
        path_file (str | None)
    """
    opener = build_opener()
    if headers:
        opener.addheaders = headers

    with opener.open(url) as response:
        content_length = response.length
        if not extract_to:
            extract_to = gettempdir()

        if n_file := response.headers.get_filename():
            file_path = os.path.join(extract_to, n_file)
        else:
            file_path = os.path.join(extract_to, Path(response.url).name)

        with open(file_path, "wb") as out_file:
            def get_resp_data():
                while True:
                    data = response.read(1024)
                    if not data:
                        break
                    yield data

            desc = f'Downloading to "{file_path}"'
            if not sys.stdout:
                print(f'{desc}...')
                for data in get_resp_data():
                    out_file.write(data)
            else:
                with tqdm(desc=desc, total=content_length, unit="B", unit_scale=True) as progress_bar:
                    for data in get_resp_data():
                        out_file.write(data)
                        progress_bar.update(len(data))

            return file_path


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
        except OSError as exc:
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
            if sys.platform == 'win32' else os.sep
        assert os.path.isdir(root_dirname)  # ...Murphy and her ironclad Law

        # Append a path separator to this directory if needed.
        root_dirname = root_dirname.rstrip(os.sep) + os.sep

        # Test whether each path component split from this pathname is valid or
        # not, ignoring non-existent and non-readable path components.
        for pathname_part in pathname.split(os.sep):
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
        matching_vals (list(str)): Lista de valores a comparar

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
    matchings = {jellyfish.jaro_winkler_similarity(search_val, match_val): match_val
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


def zip_files(zip_path, file_paths, base_path=None, compression=ZIP_DEFLATED):
    """
    Comprime los ficheros indicados con :file_paths en un fichero zip (:zip_path)

    Args:
        zip_path:
        file_paths (list or generator):
        base_path (srt=None): path desde el que se mantiene la ruta relativa de los ficheros se mantendra
        compression (int=ZIP_DEFLATED): 0 (ZIP_STORED) si no se quiere comprimir

    Returns:
        zip_path (str)
    """
    with ZipFile(zip_path, "w", compression=compression, allowZip64=True) as my_zip:
        for file_path in file_paths:
            if base_path:
                re_base_path = re.compile(os.path.normpath(base_path).replace(os.sep, '/'), re.IGNORECASE)
                arch_name = re_base_path.sub('', os.path.normpath(file_path).replace(os.sep, '/'))
            else:
                arch_name = os.path.basename(file_path)

            my_zip.write(file_path, arcname=arch_name)

    return zip_path


def zip_dir(dir_path, zip_path=None, relative_dirs_sel=None, func_filter_path=None, compression=ZIP_DEFLATED):
    """
    Comprime la carpeta indicada

    Args:
        dir_path (str): path directorio
        zip_path (str=None): el path del fichero .zip a crear. Por defecto zip en el directorio padre con el mismo
                            nombre del directorio zipeado
        relative_dirs_sel (list=None): lista de paths relativos de directorios que se trataran
        func_filter_path (func=None): Func que validará si el nom del path és valid o no per retornar
        compression (int=ZIP_DEFLATED): 0 (ZIP_STORED) si no se quiere comprimir

    Returns:
        zip_file (str)
    """
    if not zip_path:
        zip_path = f'{dir_path}.zip'

    zip_file = zip_files(zip_path,
                         iter_paths_dir(dir_path,
                                        relative_dirs_sel=relative_dirs_sel,
                                        func_filter_path=func_filter_path),
                         base_path=dir_path,
                         compression=compression)

    return zip_file


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
            zip_files(zip_path, [file_path])

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
        code_alias_locale (str='es_es'):

    Returns:
        str
    """
    with different_locale(locale.locale_alias.get(code_alias_locale)):
        return pretty_text(calendar.month_name[num_month])


def file_mod_time(path_file):
    """
    Return datetime from mofification stat timestamp from file

    Args:
        path_file (str):

    Returns:
        datetime
    """
    f_mod_time = datetime.datetime.fromtimestamp(os.stat(path_file).st_mtime)

    return f_mod_time


def rows_csv(a_path_csv, header=True, sep=';', encoding="utf8"):
    """
    Itera como dicts indexados por valores primera fila (si header=True) o si no como list
    las filas del CSV pasado por parametro a_path_csv.

    Args:
        a_path_csv (str):
        header (bool=True):
        sep (str=';'): por defecto cogerá el separador que por defecto usa csv.reader
        encoding (str="utf8"):
    Yields:
        list OR dict
    """
    with open(a_path_csv, encoding=encoding) as a_file:
        csv_rdr = csv.reader(a_file, delimiter=sep if sep else ';')
        header_row = None
        for row in csv_rdr:
            if header and not header_row:
                header_row = [v.strip().lower() for v in row]
                continue

            if header_row:
                vals_row = dict(zip(header_row, row))
            else:
                vals_row = row

            if vals_row:
                yield vals_row


def subdirs_path(path):
    """
    Itera sobre los subdirectorios del path
    Args:
        path:

    Yields:
        nom_subdir, path_subdir
    """
    with os.scandir(path) as it:
        for entry in it:
            if entry.is_dir():
                yield entry.name, entry.path


def tree_subdirs(path_dir_base, relative_dirs_sel=None, last_level_as_list=False):
    """

    Args:
        path_dir_base:
        relative_dirs_sel (list=None): lista de paths relativos de directorios que se trataran
        last_level_as_list (bool=False):

    Returns:
        dict
    """
    tree = {}

    f_valid_dir = None
    valid_dirs_sel = set()
    if relative_dirs_sel:
        for dir_sel in relative_dirs_sel:
            path_dir_rel = os.path.join(path_dir_base, dir_sel)
            if os.path.exists(path_dir_rel):
                valid_dirs_sel.add(os.path.normpath(os.path.relpath(path_dir_rel, path_dir_base)).lower())

        def valid_dir(dir_path):
            valid = False
            rel_path = os.path.relpath(dir_path, path_dir_base).lower()
            for dir_sel in valid_dirs_sel:
                if rel_path == dir_sel or os.path.commonpath((rel_path, dir_sel)):
                    valid = True
                    break

            return valid

        f_valid_dir = valid_dir

    for dir_name, dir_path in subdirs_path(path_dir_base):
        if not f_valid_dir or f_valid_dir(dir_path):
            dir_path_rel = os.path.relpath(dir_path, path_dir_base).lower()
            dirs_sel_path = [os.path.relpath(dir_sel, dir_path_rel) for dir_sel in valid_dirs_sel
                             if os.path.commonpath((dir_path_rel, dir_sel))]
            tree[dir_name] = tree_subdirs(dir_path, dirs_sel_path)

    if tree:
        if last_level_as_list and not any(tree.values()):
            tree = [*tree.keys()]

    return tree


def tree_paths(path_dir_base, relative_dirs_sel=None, func_filter_path=None, solo_dirs=False):
    """
    Retorna diccionario con el arbol de paths disponibles en el path indicado.

    Con la función F_VALID (-> bool) se podrà filtrar los paths a retornar (por defecto siempre True)

    Args:
        path_dir_base (str):
        relative_dirs_sel (list=None): lista de paths relativos de directorios que se trataran
        func_filter_path (func=None): Func que validará si el nom del path és valid o no per retornar
        solo_dirs (bool=False):

    Returns:
        dict
    """
    paths = dict()

    valid_dirs_sel = set()
    if relative_dirs_sel:
        for dir_sel in relative_dirs_sel:
            path_dir_rel = os.path.join(path_dir_base, dir_sel)
            if os.path.exists(path_dir_rel):
                valid_dirs_sel.add(path_dir_rel)

    for dir_path, dir_names, file_names in os.walk(path_dir_base):
        if valid_dirs_sel and not any(
                os.path.samefile(dir_path, a_dir_sel) or is_path_child_from(dir_path, a_dir_sel)
                for a_dir_sel in valid_dirs_sel):
            continue

        dir_path = os.path.relpath(dir_path, path_dir_base)
        dir_name = os.path.basename(dir_path)

        if func_filter_path and not func_filter_path(dir_name):
            continue

        files_selected = {fn: None for fn in file_names
                          if not func_filter_path or func_filter_path(fn)}

        if files_selected:
            subdir_paths = paths
            # En el caso del primer nivel no se guarda name directorio
            if dir_path != '.':
                for d in dir_path.split(os.sep):
                    if d not in subdir_paths:
                        subdir_paths[d] = dict()
                    subdir_paths = subdir_paths[d]

            if not solo_dirs:
                subdir_paths.update(files_selected)

    return paths


def iter_tree_paths(tree_paths, path_base=None):
    """

    Args:
        tree_paths (dict):
        path_base (str=None):

    Yields:
        path_file
    """
    for path, sub_tree in tree_paths.items():
        if sub_tree and isinstance(sub_tree, dict):
            for sub_path in iter_tree_paths(sub_tree, path):
                yield os.path.join(path_base, sub_path) if path_base else sub_path
        else:
            yield os.path.join(path_base, path) if path_base else path


def iter_paths_dir(path_dir_base, relative_dirs_sel=None, func_filter_path=None):
    """
    Itera el arbol de paths disponibles en el path indicado.

    Con la función F_VALID (-> bool) se podrà filtrar los paths a retornar (por defecto siempre True)

    Args:
        path_dir_base (str):
        relative_dirs_sel (list=None): lista de paths relativos de directorios que se trataran
        func_filter_path (func=None): Func que validará si el nom del path és valid o no per retornar

    Yields:
        path (str)
    """
    for path in iter_tree_paths(tree_paths(path_dir_base, relative_dirs_sel, func_filter_path), path_dir_base):
        yield path


def is_path_child_from(path, path_parent):
    """
    Retorna si path es hijo de path_parent

    Args:
        path:
        path_parent:

    Returns:
        bool
    """
    p_path = Path(path)
    p_path_parent = Path(path_parent)

    return any(p.samefile(p_path_parent) for p in p_path.parents)


def machine_name():
    """
    Retorna el nombre de la maquina

    Returns:
        str
    """
    # TODO - Get host from docker machine when we are in a container
    # TODO - import docker
    # TODO -
    # TODO - client = docker.from_env()
    # TODO - container_info = client.containers.get(socket.gethostname())
    # TODO - docker_host_ip = container_info.attrs['NetworkSettings']['IPAddress']
    # TODO - print(docker_host_ip)

    return socket.getfqdn().upper()


def machine_apb():
    """
    Retorna el nombre de la maquina

    Returns:
        bool
    """
    return socket.getfqdn().lower().endswith('.apb.es')


def find_key_values(obj: Any, target_key: str) -> Generator[Tuple[Any, int], None, None]:
    """
    Generator that recursively walks `obj` (dicts, lists, tuples, sets)
    and yields tuples (value, level) for every occurrence of `target_key`.

    Args:
        obj (Any): The object to search through.
        target_key (str): The key to search for.

    Yields:
        Tuple[Any, int]: A tuple containing the value associated with `target_key` and its depth level.
    """
    def _recurse(current_obj: Any, current_level: int = 0) -> Generator[Tuple[Any, int], None, None]:
        if isinstance(current_obj, dict):
            for k, v in current_obj.items():
                if k == target_key:
                    yield v, current_level
                yield from _recurse(v, current_level + 1)
        elif isinstance(current_obj, (list, tuple, set)):
            for item in current_obj:
                yield from _recurse(item, current_level + 1)

    yield from _recurse(obj)


if __name__ == '__main__':
    import fire

    fire.Fire()
