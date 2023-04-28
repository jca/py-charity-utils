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
        {
            "amount_due": "INV123",
            "balance": "Balance",
            "charge_date": "",
            "gocardless_email": "",
            "invoice_date": "",
            "item_lines.0.amount": "Item 1",
            "item_lines.1.amount": "Item 2",
            "parent_email": "Email parent",
            "parent_id": "",
            "payment_method": "",
        },
        {
            "amount_due": 12.34,
            "balance": 0,
            "charge_date": "",
            "gocardless_email": "m.c@test.email",
            "invoice_date": "2023-02-06",
            "item_lines.0.amount": 10,
            "item_lines.1.amount": 2.34,
            "parent_email": "m.c@test.email",
            "parent_id": "ID123",
            "payment_method": "gocardless",
        }
    ])

    payments_df = process_payments(gocardless_customer_df, invoice_df)

    expected_payments_df = pandas.DataFrame([
        {
            "customer.company_name": "",
            "customer.email": "m.c@test.email",
            "customer.family_name": "C",
            "customer.given_name": "M",
            "customer.id": "CU1",
            "mandate.id": "MD1",
            "payment.amount": 12.34,
            "payment.charge_date": "",
            "payment.currency": "GBP",
            "payment.description": "INV123/ID123 - Item 1, Item 2",
            "payment.metadata.INVOICE_DATE": "2023-02-06",
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
        {
            "amount_due": "INV123",
            "balance": "Balance",
            "charge_date": "",
            "gocardless_email": "",
            "invoice_date": "",
            "item_lines.0.amount": "Item 1",
            "item_lines.1.amount": "Item 2",
            "parent_email": "Email parent",
            "parent_id": "",
            "payment_method": "",
        },
        {
            "amount_due": 10,
            "balance": 0,
            "charge_date": "",
            "gocardless_email": "m.c@test.email",
            "invoice_date": "2023-02-06",
            "item_lines.0.amount": 10,
            "item_lines.1.amount": 0,
            "parent_email": "m.c@test.email",
            "parent_id": "ID123",
            "payment_method": "gocardless",
        },
        {
            "amount_due": 2.34,
            "balance": 0,
            "charge_date": "",
            "gocardless_email": "m.c@test.email",
            "invoice_date": "2023-02-06",
            "item_lines.0.amount": 0,
            "item_lines.1.amount": 2.34,
            "parent_email": "m.c@test.email",
            "parent_id": "ID124",
            "payment_method": "gocardless",
        }
    ])

    with pytest.raises(AssertionError, match=r"duplicate invoices"):
        process_payments(gocardless_customer_df, invoice_df)
