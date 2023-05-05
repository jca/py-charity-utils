import pandas
import pytest

from generate_gocardless_payments_csv.command import process_payments


def assert_frames_equal(left, right, **kwds):
    pandas.testing.assert_frame_equal(left.sort_index(axis=1), right.sort_index(axis=1), check_names=False, **kwds)


def test_process_payments_succeeds():
    gocardless_customer_df = pandas.DataFrame([{
        "customer.company_name": "",
        "customer.email": "m.c@test.email",
        "customer.family_name": "C",
        "customer.given_name": "M",
        "customer.id": "CU1",
        "mandate.id": "MD1",
    }])

    invoice_df = pandas.DataFrame([
        # header rows
        {
            "meta": "header",
            "amount_due": "Total",
            "balance": "Balance",
            "gocardless_email": "",
            "item_lines.1.title": "Item 1",
            "item_lines.2.title": "Item 2",
            "payments.1.amount": "Payment",
            "parent_email": "Email parent",
            "parent_id": "Parent ID",
            "payment_method": "Methode de paiement",
        },
        {
            "meta": "charge_date",
            "amount_due": "",
            "balance": "",
            "gocardless_email": "",
            "item_lines.1.title": "",
            "item_lines.2.title": "",
            "payments.1.amount": "2023-02-15",
            "parent_email": "",
            "parent_id": "",
            "payment_method": "",
        },
        # invoice request row
        {
            "meta": "",
            "amount_due": 12.34,
            "balance": 0,
            "gocardless_email": "m.c@test.email",
            "item_lines.1.amount": "10",
            "item_lines.2.amount": "2.34",
            "payments.1.amount": "12.34",
            "parent_email": "m.c@test.email",
            "parent_id": "ID123",
            "payment_method": "gocardless",
        }
    ])

    payments_df = process_payments(
        gocardless_customer_df,
        invoice_df,
        invoice_id_prefix="INV123",
        invoice_date="2023-02-12",
        invoice_customer_id_field="parent_id",
        invoice_gocardless_email_field="gocardless_email",
        invoice_total_amount_field="amount_due",
        invoice_payment_method_field="payment_method",
        invoice_payment_method_value="gocardless",
    )

    expected_payments_df = pandas.DataFrame([
        {
            "customer.company_name": "",
            "customer.email": "m.c@test.email",
            "customer.family_name": "C",
            "customer.given_name": "M",
            "customer.id": "CU1",
            "mandate.id": "MD1",
            "payment.amount": 12.34,
            "payment.charge_date": "2023-02-15",
            "payment.currency": "GBP",
            "payment.description": "INV123/ID123/1",
            "payment.metadata.INVOICE_DATE": "2023-02-12",
            "payment.metadata.INVOICE_ID": "INV123/ID123",
        }
    ])

    assert set(payments_df.columns) == set(expected_payments_df.columns)
    assert_frames_equal(payments_df, expected_payments_df)


def test_process_payments_fails_for_duplicate_parent_email():
    gocardless_customer_df = pandas.DataFrame([{
        "customer.company_name": "",
        "customer.email": "m.c@test.email",
        "customer.family_name": "C",
        "customer.given_name": "M",
        "customer.id": "CU1",
        "mandate.id": "MD1",
    }])

    invoice_df = pandas.DataFrame([
        # header
        {
            "meta": "charge_date",
            "amount_due": "",
            "gocardless_email": "",
            "item_lines.1.amount": "",
            "item_lines.2.amount": "",
            "payments.1.amount": "2023-02-15",
            "parent_id": "",
            "payment_method": "",
        },
        # data
        {
            "meta": "",
            "amount_due": "12.34",
            "gocardless_email": "m.c@test.email",
            "item_lines.1.amount": "10",
            "item_lines.2.amount": "2.34",
            "payments.1.amount": "12.34",
            "parent_id": "ID123",
            "payment_method": "gocardless",
        },
        {
            "meta": "",
            "amount_due": "12.34",
            "gocardless_email": "m.c@test.email",
            "item_lines.1.amount": "10",
            "item_lines.2.amount": "2.34",
            "payments.1.amount": "12.34",
            "parent_id": "ID123",
            "payment_method": "gocardless",
        }
    ])

    with pytest.raises(AssertionError, match=r"duplicate invoices"):
        process_payments(
            gocardless_customer_df,
            invoice_df,
            invoice_date="2023-02-06",
            invoice_id_prefix="INV123",
            invoice_customer_id_field="parent_id",
            invoice_gocardless_email_field="gocardless_email",
            invoice_total_amount_field="amount_due",
            invoice_payment_method_field="payment_method",
            invoice_payment_method_value="gocardless",
        )
