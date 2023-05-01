"""
Generate GoCardless payment CSVs
"""
import argparse
import io
import logging
import pathlib
import re
from typing import Optional
import pandas
from datetime import date

logging.basicConfig(level=logging.WARN)
stream = io.StringIO()
logger = logging.getLogger()
handler = logging.StreamHandler(stream)
logger.addHandler(handler)


def parse_args():
    """parse args"""
    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument(
        '--input-invoice-requests-csv',
        dest='input_invoice_requests_csv',
        help='path to CSV file containing one line per invoice request',
        type=pathlib.Path,
        required=True
    )

    parser.add_argument(
        '--input-gocardless-customers-csv',
        dest='input_gocardless_customers_csv',
        help='path to GoCardless customer CSV export',
        type=pathlib.Path,
        required=True
    )

    parser.add_argument(
        '--invoice-id-prefix',
        help="invoice id prefix: the first part of the generated invoice id '<prefix>/<customer_id>'",
        required=True,
    )

    parser.add_argument(
        '--invoice-customer-id-field',
        help="id field: used to ensure there is only one invoice per customer",
        default="customer_id"
    )

    parser.add_argument(
        '--invoice-total-amount-field',
        help="total amount field: used to verify the sum of item line amounts and payment amounts",
        default="total_amount"
    )

    parser.add_argument(
        '--invoice-payment-method-field',
        help="payment method field: used to filter the input invoices to only those paid with GoCardless",
        default=None
    )

    parser.add_argument(
        '--invoice-payment-method-value',
        help="payment method value: used to filter the input invoices to only those paid with GoCardless",
        default=None
    )

    parser.add_argument(
        '--invoice-gocardless-email-field',
        help="GoCardless email field: used to join the invoice requests with the customer export",
        default="gocardless_email"
    )

    parser.add_argument(
        '--output-gocardless-payments-csv',
        dest='output_gocardless_payments_csv',
        help='path to output the GoCardless payments CSV',
        type=pathlib.Path,
        default="-",
    )

    return parser.parse_args()


def main():
    """main"""

    args = parse_args()
    gocardless_all_customers_df = pandas.read_csv(args.input_gocardless_customers_csv)
    invoice_df = pandas.read_csv(args.input_invoice_requests_csv)

    payments_df = process_payments(
        gocardless_all_customers_df,
        invoice_df,
        args.invoice_id_prefix,
        args.invoice_customer_id_field,
        args.invoice_gocardless_email_field,
        args.invoice_total_amount_field,
        args.invoice_payment_method_field,
        args.invoice_payment_method_value,
    )

    payments_df.to_csv(args.output_gocardless_payments_csv, index=False)
    logger.warn(f"Generated {args.output_gocardless_payments_csv} with {len(payments_df)} payments")


def process_payments(
    gocardless_all_customers_df: pandas.DataFrame,
    invoice_df: pandas.DataFrame,
    invoice_id_prefix: str,
    invoice_customer_id_field: str,
    invoice_gocardless_email_field: str,
    invoice_total_amount_field: str,
    invoice_payment_method_field: Optional[str],
    invoice_payment_method_value: Optional[str],
) -> pandas.DataFrame:

    # GoCardless: ensure all required customer columns are present
    required_customer_columns = {
        "mandate.id",
        "customer.id",
        "customer.given_name",
        "customer.family_name",
        "customer.company_name",
        "customer.email",
    }
    missing_gocardless_customer_df_columns = required_customer_columns.difference(gocardless_all_customers_df.columns)
    assert len(missing_gocardless_customer_df_columns) == 0, (
        f"Missing required columns from gocardless customer csv: \n"
        f"{missing_gocardless_customer_df_columns}"
    )

    # Invoice request: Ensure all required columns are present
    required_invoice_columns = {
        invoice_customer_id_field,
        invoice_gocardless_email_field,
        invoice_total_amount_field,
    }
    if invoice_payment_method_field:
        required_customer_columns.add(invoice_payment_method_field)

    missing_invoice_df_columns = required_invoice_columns.difference(invoice_df.columns)
    assert len(missing_invoice_df_columns) == 0, (
        f"Missing required columns from invoice csv: \n"
        f"{missing_invoice_df_columns}"
    )

    # Gocardless: drop duplicates
    gocardless_customers_df = gocardless_all_customers_df.drop_duplicates('customer.email', keep='last')

    # Gocardless: drop all pre-generated payment columns from gocardless csv
    non_payment_cols = [col for col in gocardless_all_customers_df.columns if "payment." not in col]
    gocardless_customers_df = gocardless_customers_df[non_payment_cols]

    # Invoice requests: apply meta rows
    if "meta" in invoice_df.columns:
        for index, row in invoice_df.iterrows():
            meta_value = row["meta"]
            if row["meta"]:
                # Add all values from row
                for column in invoice_df.columns:
                    if row[column]:
                        column_parts = column.split(".")
                        meta_column_name = ".".join(column_parts[:-1] + [meta_value])
                        invoice_df[meta_column_name] = row[column]
                invoice_df.drop(index=index, inplace=True)
            else:
                break

    title_row = {}  # TODO remove this and use csv meta-data merge instead

    item_line_amount_pattern = r'^item_lines.\d+.amount'
    item_line_amount_columns = [col for col in invoice_df.columns if re.match(item_line_amount_pattern, col)]
    assert item_line_amount_columns, (
        "There must be `item_lines.<number>.amount` columns in the invoice request csv"
    )

    payment_amount_pattern = r'^payments.(\d+).amount'
    payment_amount_columns = [col for col in invoice_df.columns if re.match(payment_amount_pattern, col)]
    assert payment_amount_columns, (
        "There must be `payments.<number>.amount` columns in the invoice request csv"
    )

    # Invoice requests: cast amount columns to numeric
    for col in [invoice_total_amount_field, *item_line_amount_columns, *payment_amount_columns]:
        invoice_df[col] = pandas.to_numeric(invoice_df[col])

    # Invoice requests: Validate that the sum of item_lines is equal to sum of charge amount and total of invoice
    invoice_df["unmatched_amounts"] = \
        abs(invoice_df[invoice_total_amount_field] - sum(invoice_df[col] for col in item_line_amount_columns)) + \
        abs(invoice_df[invoice_total_amount_field] - sum(invoice_df[col] for col in payment_amount_columns))

    invoice_with_sum_difference_df = invoice_df[invoice_df["unmatched_amounts"] > 0]
    assert len(invoice_with_sum_difference_df) == 0, (
        f"There are {len(invoice_with_sum_difference_df)} invoices with invalid amounts:"
        f"{invoice_with_sum_difference_df}"
    )

    # Invoice requests: Check whether there are multiple invoice requests per customer
    duplicate_customers_idx = invoice_df[invoice_customer_id_field].duplicated()
    duplicate_customers_df = invoice_df[duplicate_customers_idx]
    assert duplicate_customers_df.size == 0, (
        f"There are customers with duplicate invoices:"
        f"{duplicate_customers_df}"
    )

    # Invoice requests: Retain only invoices which should be paid with GoCardless
    if invoice_payment_method_field and invoice_payment_method_value:
        other_payment_method_invoice_idx = invoice_df[invoice_payment_method_field] != invoice_payment_method_value
        gocardless_invoice_df = invoice_df[~other_payment_method_invoice_idx]
        if len(gocardless_invoice_df) < len(invoice_df):
            other_payment_method_invoice_df = invoice_df[other_payment_method_invoice_idx]
            logger.warn(
                f"There are {len(other_payment_method_invoice_df)} invoices with other payment method: \n"
                f"{other_payment_method_invoice_df[[invoice_customer_id_field, 'payment_method']]}"
            )
            logger.info(f"There are {len(gocardless_invoice_df)} invoices with gocardless: \n{gocardless_invoice_df}")

    elif not invoice_payment_method_field and not invoice_payment_method_value:
        gocardless_invoice_df = invoice_df

    else:
        raise ValueError("--invoice-payment-method-field and --invoice-payment-method-value must be provided together")

    # Invoice requests: Check that all invoices have positive amounts
    void_invoice_df = gocardless_invoice_df[gocardless_invoice_df[invoice_total_amount_field] <= 0]
    if len(void_invoice_df) > 0:
        assert len(void_invoice_df) == 0, (
            f"There are {len(void_invoice_df)} void invoices with gocardless setup. "
            "Please set another payment method and handle these separately\n"
            f"{void_invoice_df}"
        )

    # Merge GoCardless customer data
    merged_gocardless_invoice_df = pandas.merge(
        left=gocardless_invoice_df,
        left_on=gocardless_invoice_df['gocardless_email'].str.lower(),
        right=gocardless_customers_df,
        right_on=gocardless_customers_df['customer.email'].str.lower(),
        how='left',
    )

    # Verify whether any GoCardless customer is missing
    missing_gocardless_customer_invoice_idx = merged_gocardless_invoice_df["customer.id"].isna()
    missing_gocardless_customer_invoice_df = merged_gocardless_invoice_df[missing_gocardless_customer_invoice_idx]
    assert len(missing_gocardless_customer_invoice_df) == 0, (
        f"There are {len(missing_gocardless_customer_invoice_df)} invoices with missing gocardless account:"
        f"{missing_gocardless_customer_invoice_df}"
    )

    logger.info(
        f"There are {len(merged_gocardless_invoice_df)} invoices to process with gocardless:"
        f"{merged_gocardless_invoice_df}"
    )

    # Invoice requests: Build up invoice id
    merged_gocardless_invoice_df["payment.metadata.INVOICE_ID"] = \
        f"{invoice_id_prefix}/" + merged_gocardless_invoice_df[invoice_customer_id_field]
    merged_gocardless_invoice_df["payment.metadata.INVOICE_DATE"] = date.today()

    # Scatter over payments

    payment_dfs = []

    for payment_amount_column in payment_amount_columns:
        # Find the payment date and payment id
        match = re.match(payment_amount_pattern, payment_amount_column)
        if not match:
            raise ValueError("payment amount column did not match pattern")

        payment_id = match.group(1)
        df = merged_gocardless_invoice_df.copy()
        df["payment.description"] = df["payment.metadata.INVOICE_ID"] + f"/{payment_id}"
        df["payment.charge_date"] = title_row[payment_amount_column]
        df["payment.amount"] = df[payment_amount_column]
        df["payment.currency"] = "GBP"
        payment_dfs.append(df)

    payment_df = pandas.concat(payment_dfs, axis=0)

    # Map invoice csv to GoCardless payment csv
    gocardless_columns = [
        "mandate.id",
        "customer.id",
        "customer.given_name",
        "customer.family_name",
        "customer.company_name",
        "customer.email",
        "payment.amount",
        "payment.currency",
        "payment.description",
        "payment.charge_date",
        "payment.metadata.INVOICE_ID",
        "payment.metadata.INVOICE_DATE",
    ]

    # Check that sum of payments is the same as sum of invoices
    cumulated_payment_amount = payment_df["payment.amount"].sum()
    cumulated_invoice_amount = gocardless_invoice_df[invoice_total_amount_field].sum()

    assert cumulated_payment_amount == cumulated_invoice_amount, (
        f"There is a difference between {cumulated_invoice_amount=} and {cumulated_payment_amount=} \n"
        f"{payment_df=} \n"
        f"{gocardless_invoice_df=} \n"
    )

    return payment_df[gocardless_columns]
