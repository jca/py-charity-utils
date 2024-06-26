"""
Send templated HTML emails with pdf attachments templated from HTML
"""
import argparse
from datetime import date
from distutils.dir_util import copy_tree
import io
import logging
import os
from tempfile import TemporaryDirectory
from jinja2 import Environment, FileSystemLoader, select_autoescape
import pandas
import pdfkit  # type: ignore
from send_mail_with_attachment.mail import get_smtp_server, prepare_message
from shared.csv_utils import expand_record_lists, process_csv_with_metadata

SMTP_HOST = os.environ['SMTP_HOST']
SMTP_PORT = os.environ['SMTP_PORT']
SMTP_USER = os.environ['SMTP_USERNAME']
SMTP_PASSWORD = os.environ['SMTP_PASSWORD']

logging.basicConfig(level=logging.DEBUG)
stream = io.StringIO()
logger = logging.getLogger()
handler = logging.StreamHandler(stream)
logger.addHandler(handler)


def parse_args():
    """parse args"""
    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument(
        '--input-request-csv',
        help='path to CSV file containing one line per email with attachment to generate',
        required=True
    )

    parser.add_argument(
        '--id-field',
        help="id field (used to suffix attachments filenames)",
        default="id"
    )

    parser.add_argument(
        '--email-field',
        help="email field (used to send emails)",
        default="email"
    )

    parser.add_argument(
        '--email-sender',
        help="email sender",
        default=SMTP_USER
    )

    parser.add_argument(
        '--email-reply-to',
        help="email for reply-to",
        default=None
    )

    parser.add_argument(
        '--email-subject',
        help="email subject",
        required=True
    )

    parser.add_argument(
        '--input-email-template-html',
        help='path to HTML file containing the template for the email',
        required=True
    )

    parser.add_argument(
        '--input-attachment-template-html',
        help='HTML file containing attachment', required=True
    )

    parser.add_argument(
        '--attachment-file-prefix',
        help='attachment file prefix', required=True
    )

    parser.add_argument(
        '--output-dir', required=True,
        help="path to write all output"
    )

    parser.add_argument(
        '--force',
        help="use this flag to actually send out emails",
        action='store_true'
    )

    return parser.parse_args()


def main():
    """main"""

    args = parse_args()

    smtp_server = get_smtp_server(
        SMTP_HOST,
        SMTP_PORT,
        SMTP_USER,
        SMTP_PASSWORD,
    )
    id_field = args.id_field
    email_field = args.email_field
    email_subject = args.email_subject
    email_sender = args.email_sender
    email_reply_to = args.email_reply_to
    attachment_file_prefix = args.attachment_file_prefix

    raw_invoice_df = pandas.read_csv(args.input_request_csv)
    invoice_df = process_csv_with_metadata(input_df=raw_invoice_df)

    if id_field not in invoice_df.columns:
        raise ValueError(
            f"{invoice_df.columns=} must contain --id-field ({args.id_field})")
    if email_field not in invoice_df.columns:
        raise ValueError(
            f"{invoice_df.columns=} must contain --email-field ({email_field})"
        )

    email_jinja_env = Environment(
        loader=FileSystemLoader(os.path.dirname(
            args.input_email_template_html)),
        autoescape=select_autoescape()
    )
    email_template = email_jinja_env.get_template(
        os.path.basename(args.input_email_template_html))

    attachment_jinja_env = Environment(
        loader=FileSystemLoader(os.path.dirname(
            args.input_attachment_template_html)),
        autoescape=select_autoescape()
    )
    attachment_template = attachment_jinja_env.get_template(
        os.path.basename(args.input_attachment_template_html))

    output_dir = os.path.realpath(args.output_dir)
    attachment_pdf_paths = []

    messages = []
    with TemporaryDirectory(prefix="py-charity-utils_") as tmp_dir_path:
        copy_tree(os.path.dirname(
            args.input_attachment_template_html), tmp_dir_path)

        for (i, record) in invoice_df.iterrows():
            id = str(record[id_field])
            recipient_email = record[email_field]

            if id.strip() == "":
                raise ValueError(f"{record=} must contain an {id_field}")
            if recipient_email.strip() == "":
                raise ValueError(f"{record=} must contain an {email_field}")

            attachment_html_path = f'{tmp_dir_path}/{attachment_file_prefix}{id}.html'
            attachment_pdf_path = f'{output_dir}/{attachment_file_prefix}{id}.pdf'

            structured_record = expand_record_lists(record)
            structured_record["today"] = date.today().strftime("%d/%m/%Y")
            structured_record["attachment_file_prefix"] = attachment_file_prefix
            email_html = email_template.render(**structured_record)
            attachment_html = attachment_template.render(**structured_record)
            with open(attachment_html_path, 'w', encoding="utf-8") as attachment_file:
                attachment_file.write(attachment_html)

            pdfkit.from_file(attachment_html_path, attachment_pdf_path, options={
                "enable-local-file-access": None,
                "disable-smart-shrinking": '',
                'page-size': 'A4',
                'dpi': 400,
            })

            attachment_pdf_paths.append(attachment_pdf_path)

            logging.info(
                "written %s bytes at %s", os.path.getsize(attachment_pdf_path), attachment_pdf_path)

            messages.append((recipient_email, email_subject, email_html, attachment_pdf_path))

        log_prefix = "skipped"
        if args.force:
            log_prefix = ""

        # Send all emails
        for (recipient_email, email_subject, email_html, attachment_pdf_path) in messages:
            logging.info(f"{log_prefix} sending email to {recipient_email}: {os.path.basename(attachment_pdf_path)}")
            if args.force:
                message = prepare_message(
                    email_sender,
                    recipient_email,
                    email_reply_to,
                    email_subject,
                    email_html,
                    [
                        attachment_pdf_path,
                    ],
                )
                smtp_server.send_message(message)

    logging.info(f"successfully sent {len(messages)} messages")

    report_message = prepare_message(
        email_sender,
        email_sender,
        email_reply_to,
        f"Email sendout report: {email_subject}",
        f"Last email sent:"
        f"<hr>{email_html}<hr>"
        f"Send-out log: <pre>{stream.getvalue()}</pre>",
        attachment_pdf_paths,
    )

    logging.info(f"successfully sent report to {email_sender}")

    smtp_server.send_message(report_message)

    smtp_server.quit()
