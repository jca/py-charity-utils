import pandas

from shared.csv_utils import process_csv_with_metadata


def assert_frames_equal(left: pandas.DataFrame, right: pandas.DataFrame, **kwds):
    assert left.to_json(indent=4, orient="records") == right.to_json(indent=4, orient="records")


def test_read_csv_with_metadata():
    df = pandas.DataFrame([
        # header rows
        {
            "meta": "header",
            "amount_due": "Total",
            "item_lines.1.amount": "Item 1",
            "payments.0.amount": "Payment",
        },
        {
            "meta": "charge_date",
            "amount_due": "",
            "item_lines.1.amount": "",
            "payments.0.amount": "2023-02-01",
        },
        # invoice request row
        {
            "meta": "",
            "amount_due": "123.45",
            "item_lines.1.amount": "123.45",
            "payments.0.amount": "123.45",
        },
    ])

    processed_df = process_csv_with_metadata(df)

    expected_df = pandas.DataFrame([
        {
            "meta": "",
            "amount_due": "123.45",
            "item_lines.1.amount": "123.45",
            "payments.0.amount": "123.45",
            "item_lines.1.header": "Item 1",  # Added by meta row "header"
            "payments.0.header": "Payment",  # Added by meta row "header"
            "payments.0.charge_date": "2023-02-01",  # Added by meta row "charge_date"
        },
    ])

    assert set(processed_df.columns) == set(expected_df.columns)
    assert_frames_equal(processed_df, expected_df)
