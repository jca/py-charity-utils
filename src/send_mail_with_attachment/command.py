"""
Send templated HTML emails with pdf attachments templated from HTML
"""
import argparse
from distutils.dir_util import copy_tree
import io
import logging
import os
from tempfile import TemporaryDirectory
from jinja2 import Environment, FileSystemLoader, select_autoescape
import json
import pandas
import pdfkit  # type: ignore
import re
from send_mail_with_attachment.mail import get_smtp_server, prepare_message

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
    attachment_file_prefix = args.attachment_file_prefix

    request_df = pandas.read_csv(args.input_request_csv)
    if id_field not in request_df.columns:
        raise ValueError(
            f"{request_df.columns=} must contain --id-field ({args.id_field})")
    if email_field not in request_df.columns:
        raise ValueError(
            f"{request_df.columns=} must contain --email-field ({email_field})"
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

    # Extract title rows
    title_row = None
    for index, row in request_df.iterrows():
        if "@" not in row[args.email_field]:
            if title_row is None:
                title_row = row
            request_df.drop(index=index, inplace=True)
        else:
            break

    assert title_row is not None, (
        "The second row of the CSV must be a title row which contains item line descriptions"
    )

    item_line_pattern = r'^(\w+)\.(\d+)\.(\w+)'
    for col in request_df.columns:
        match = re.match(item_line_pattern, col)
        if match:
            title_type = title_row[0] or "title"
            item_line_description_field = f"{match[1]}.{match[2]}.{title_type}"
            request_df[item_line_description_field] = title_row[col]

    with TemporaryDirectory(prefix="pymailtpl") as tmp_dir_path:
        copy_tree(os.path.dirname(
            args.input_attachment_template_html), tmp_dir_path)

        for (i, record) in request_df.iterrows():
            id = record[id_field]
            recipient_email = record[email_field]

            if id.strip() == "":
                raise ValueError(f"{record=} must contain an {id_field}")
            if recipient_email.strip() == "":
                raise ValueError(f"{record=} must contain an {email_field}")

            attachment_html_path = f'{tmp_dir_path}/{attachment_file_prefix}-{id}.html'
            attachment_pdf_path = f'{output_dir}/{attachment_file_prefix}-{id}.pdf'

            structured_record = expand_record_lists(record)
            print(json.dumps(structured_record, indent=2))

            email_html = email_template.render(**structured_record)
            attachment_html = attachment_template.render(**structured_record)
            with open(attachment_html_path, 'w', encoding="utf-8") as attachment_file:
                attachment_file.write(attachment_html)

            pdfkit.from_file(attachment_html_path, attachment_pdf_path, options={
                "enable-local-file-access": None,
                "disable-smart-shrinking": None,
            })

            attachment_pdf_paths.append(attachment_pdf_path)

            logging.info(
                "written %s bytes at %s", os.path.getsize(attachment_pdf_path), attachment_pdf_path)

            message = prepare_message(
                SMTP_USER,
                [recipient_email],
                email_subject,
                email_html,
                [
                    attachment_pdf_path,
                ],
            )

            log_prefix = "skipped"
            if args.force:
                smtp_server.send_message(message)
                log_prefix = ""

            logging.info(f"{log_prefix} sending email %i to %s: %s", i,
                         recipient_email, os.path.basename(attachment_pdf_path))

    logging.info("successfully sent %i messages", len(attachment_pdf_paths))

    smtp_server.send_message(prepare_message(
        SMTP_USER,
        [SMTP_USER],
        f"Email sendout record: {email_subject}",
        f"Last email sent:"
        f"<hr>{email_html}<hr>"
        f"Send-out log: <pre>{stream.getvalue()}</pre>",
        attachment_pdf_paths,
    ))

    smtp_server.quit()


Record = dict[str, float | str | "Record"]


def expand_record_lists(record: dict[str, str], separator='.'):
    """
    Transform a flat csv row into a row containing lists of dictionaries
    For example, `field.123.subfield` will be transformed into a structure
    of shape     `field[123][subfield]`
    """
    output_record: Record = {}
    for field, value in record.items():
        parts = field.rsplit(separator, maxsplit=3)
        if len(parts) == 3:
            [output_field, index, output_subfield] = parts
            if output_field not in output_record:
                output_record[output_field] = {}
            if index not in output_record[output_field]:  # type: ignore
                output_record[output_field][index] = {}  # type: ignore
            output_record[output_field][index][output_subfield] = value  # type: ignore
        else:
            output_record[field] = value
    return output_record
