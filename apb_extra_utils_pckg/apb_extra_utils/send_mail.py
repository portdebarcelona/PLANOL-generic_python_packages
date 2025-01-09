#  coding=utf-8
#
#  Author: Ernesto Arredondo Martinez (ernestone@gmail.com)
#  Created: 7/6/19 18:23
#  Last modified: 7/6/19 18:21
#  Copyright (c) 2019

# Functions to send mail from a server (environment variable MAIL_SERVER)

import datetime
import mimetypes
import os
import smtplib
import ssl
import warnings

import docutils.core
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from .misc import machine_apb, machine_name


def set_attachment_to_msg(msg, file_path):
    """

    Args:
        msg (EmailMessage): objecto EmailMessage donde se hara attach
        file_path: path del fichero a vincular al mensaje

    Returns:

    """
    if not os.path.isfile(file_path):
        return

    # Guess the content type based on the file's extension.  Encoding
    # will be ignored, although we should check for simple things like
    # gzip'd or compressed files.
    ctype, encoding = mimetypes.guess_type(file_path)
    if ctype is None or encoding is not None:
        # No guess could be made, or the file is encoded (compressed), so
        # use a generic bag-of-bits type.
        ctype = 'application/octet-stream'
    maintype, subtype = ctype.split('/', 1)
    with open(file_path, 'rb') as fp:
        msg.add_attachment(fp.read(),
                           maintype=maintype,
                           subtype=subtype,
                           filename=os.path.basename(file_path))


def sendMailWithAttach(server=os.environ.get('MAIL_SERVER', 'server-mail.com'), frm='', to='', subject='', body='',
                       lineSep='not_line_separator', files=None, to_html=False, tls=True):
    """
    Permet enviar un E-mail des de FROM a TO amb SUBJECT amb BOBY line_separator (cas body amb multilinea) i ATTACH

    Args:
        server (str=os.environ.get('MAIL_SERVER'):
        frm (str=""):
        to (str=""):
        subject (str=""):
        body (str=""):
        lineSep (str="not_line_separator"):
        files (list=None): lista de paths de ficheros a adjuntar
        to_html (bool=False): Si true parsea con docutils (reestructuredText [rst], Latex, ...)
                              el texto del body enviado y lo convierte a html
        tls (bool=True): start TLS
    Returns:

    """
    from email.message import EmailMessage

    msg = EmailMessage()

    msg['From'] = frm
    msg['To'] = to
    msg['Subject'] = subject
    msg.epilogue = ''

    if lineSep != 'not_line_separator' and body.find(lineSep) >= 0:
        body = '\n'.join(body.split(lineSep))

    msg.set_content(body)
    if to_html:
        msg.add_alternative(docutils.core.publish_string(body, writer_name="html").decode('utf-8'), subtype='html')

    if files:
        for file_path in files:
            set_attachment_to_msg(msg, file_path)

    context = None
    if tls:
        context = ssl.create_default_context()
    srv = None
    try:
        codi = 0
        srv = smtplib.SMTP(server)
        srv.ehlo()
        if tls:
            try:
                srv.starttls(context=context)
            except smtplib.SMTPNotSupportedError as exc:
                print(f"El server SMTP '{server}' no suporta TLS. Error: {exc}")
        srv.ehlo()
        srv.send_message(msg)
    except smtplib.SMTPException as exc:
        import traceback
        print(traceback.format_exc())
        codi = 1
    finally:
        if srv:
            srv.quit()

    return codi


FROM_MAIL = os.getenv('DEFAULT_FROM_MAIL', 'from_your_account@mail.com')


def enviar_mail(subject, body, user_mail_list, to_html=False, *attach_path_files):
    """
    Envia mail desde la cuenta FROM_MAIL a la lista de mails especificados y adjunta los logs del gestor
    si estos han generado entradas

    Args:
        subject (str): Le asignará el nombre de la máquina desde la que está corriendo
        body (str): Texto con el cuerpo del mail. Por defecto buscará '$$NEWLINE$$' para substituir por saltos de línea
        user_mail_list (list): Lista de strings con los correos
        to_html (bool=False): Si true parsea con docutils (reestructuredText [rst], Latex, ...)
                      el texto del body enviado y lo convierte a html
        *attach_path_files: PATHs de ficheros a adjuntar

    Returns:
        codi (int)
    """
    codi = 1
    if machine_apb():
        subject = f"[{machine_name()}] {subject}"

    # SendMail
    try:
        codi = sendMailWithAttach(frm=FROM_MAIL,
                                  to=", ".join(user_mail_list),
                                  subject="{} {}".format(subject,
                                                         datetime.datetime.now().strftime(
                                                             '%Y-%m-%d %H:%M')),
                                  body=body,
                                  lineSep='$$NEWLINE$$',
                                  files=list(attach_path_files),
                                  to_html=to_html)

    except Exception as exc:
        import traceback
        print(traceback.format_exc())
        warnings.warn("No se ha podido enviar el mail con subject '{subject}'".format(subject=subject))

    return codi


def send_grid(subject: str, body: str, user_mail_list: list, sender: str = None, api_key: str = None):
    """
    Envia mail desde la api de sendGrid

    Args:
        subject (str): Tema a enviar en el correo
        body (str): Texto con el cuerpo del mail. Por defecto buscará '$$NEWLINE$$' para substituir por saltos de línea
        user_mail_list (list): Lista de strings con los correos
        sender (str=None): Mail del sender. Si no el passen, agafem variable d'entorn SENDGRID_SENDER
        api_key(str=None): Api key del send grid a utilitzar. Si no el passen, agafem variable d'entorn SENDGRID_API_KEY

    Returns:
        dict: Diccionario con la respuesta de la api de sendGrid
            Examples:
                OK = {'status_code': 202, 'body': ...}

    """
    if not api_key:
        api_key = os.getenv('SENDGRID_API_KEY')

    if not sender:
        sender = os.getenv('SENDGRID_SENDER')

    resp = dict()
    try:
        message = Mail(
            from_email=sender,
            to_emails=user_mail_list,
            subject=subject,
            html_content=body)

        sg = SendGridAPIClient(api_key)
        response = sg.send(message)

        resp['status_code'] = response.status_code
        resp['body'] = response.body

    except Exception as exc:
        error = f"No se ha podido enviar el mail con subject '{subject}'\n" \
                f"Error: {exc}"
        resp['error'] = error
        warnings.warn(error)

    return resp


if __name__ == '__main__':
    import fire

    fire.Fire({
        enviar_mail.__name__: enviar_mail,
        send_grid.__name__: send_grid
    })
