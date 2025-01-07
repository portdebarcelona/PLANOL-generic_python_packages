#  coding=utf-8
#
#  Author: Ernesto Arredondo Martinez (ernestone@gmail.com)
#  Created: 
#  Copyright (c)
"""
.. include:: ../README.md
"""

import os
import shutil
import tempfile
from pathlib import Path
from platform import system
from zipfile import ZipFile

from apb_extra_utils.misc import download_and_unzip


def set_instantclient_oracle():
    """
    Set the instant client oracle 64bits to use gestor oracle

    Returns:
        setted (bool)
    """
    instant_client = os.getenv('INSTANT_CLIENT_NAME', 'instantclient_oracle')
    local_path_instant_client = os.getenv('PATH_INSTANT_CLIENT_ORACLE', os.path.join(Path.home(), instant_client))
    if not os.path.exists(local_path_instant_client):
        tempdir = tempfile.gettempdir()
        path_extract = os.path.join(tempdir, instant_client)

        path_instant_client_zip = os.getenv('PATH_INSTANT_CLIENT_ORACLE_ZIP', '')
        # Path zip
        if os.path.exists(path_instant_client_zip):
            zip_name = f'{instant_client}.zip'
            temp_zip = os.path.join(tempdir, zip_name)
            if not os.path.exists(temp_zip):
                shutil.copy(path_instant_client_zip, tempdir)
            zipfile = ZipFile(temp_zip)
            zipfile.extractall(path=path_extract)
        else:
            # Decide wich system
            sys_name = system().lower()
            url_instant_client = None
            if sys_name == 'windows':
                url_instant_client = os.getenv(
                    'URL_INSTANT_CLIENT_ORACLE_WINDOWS',
                    'https://download.oracle.com/otn_software/nt/instantclient/instantclient-basiclite-windows.zip')
            elif sys_name == 'linux':
                url_instant_client = os.getenv(
                    'URL_INSTANT_CLIENT_ORACLE_LINUX',
                    'https://download.oracle.com/otn_software/linux/instantclient/instantclient-basiclite-linuxx64.zip')

            if url_instant_client:
                download_and_unzip(url_instant_client, path_extract)

        if os.path.exists(path_extract):
            instant_temp_path = os.path.join(path_extract, next(iter(os.listdir(path_extract)), ''))
            if os.path.exists(instant_temp_path):
                shutil.move(instant_temp_path, local_path_instant_client)

    if os.path.exists(local_path_instant_client) and \
            not any(os.path.samefile(local_path_instant_client, p) for p in os.get_exec_path() if os.path.exists(p)):
        prev_path = os.getenv('PATH')
        os.environ['PATH'] = f'{local_path_instant_client};{prev_path}'
        print(f'Set PATH with instant_client "{local_path_instant_client}"')


set_instantclient_oracle()
