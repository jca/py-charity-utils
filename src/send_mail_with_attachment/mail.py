"""
Mail functions
"""

import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate
from os.path import basename
from typing import List


def get_smtp_server(host: str, port: int, user: str, password: str) -> smtplib.SMTP:
    "Prepares smtp server instance from environment variables"

    server = smtplib.SMTP_SSL(host, port)
    server.ehlo()
    server.login(user, password)
    return server


def prepare_message(
    send_from: str,
    send_to: str,
    reply_to: str | None,
    subject: str,
    html: str,
    file_paths: List[str],
):
    """send an email with HTML, alt. text and attachments"""

    msg = MIMEMultipart()
    msg['From'] = send_from
    msg['To'] = send_to
    msg['Date'] = formatdate(localtime=True)
    msg['Subject'] = subject

    if reply_to:
        msg['Reply-To'] = reply_to

    msg.attach(MIMEText(html, 'html'))

    for file_path in file_paths or []:
        attachment_name = basename(file_path)
        with open(file_path, "rb") as file_handle:
            part = MIMEApplication(
                file_handle.read(),
                Name=attachment_name
            )
        # After the file is closed
        part['Content-Disposition'] = f'attachment; filename="{attachment_name}"'
        msg.attach(part)

    return msg
