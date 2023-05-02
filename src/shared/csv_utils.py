import pandas


def process_csv_with_metadata(input_df: pandas.DataFrame) -> pandas.DataFrame:
    """"
    Transforms a CSV with an optional meta column and header rows by appending the meta rows into the dataframe.

    For an input dataframe:
    ```
           meta amount_due item_lines.1.amount payments.0.amount
         header      Total              Item 1           Payment
    charge_date                                       2023-02-01
                    123.45              123.45            123.45
    ```

    The function returns:
    ```
    meta amount_due item_lines.1.amount payments.0.amount item_lines.1.header payments.0.header payments.0.charge_date
             123.45              123.45            123.45              Item 1           Payment             2023-02-01
    ```
    """
    output_df = input_df.copy(deep=True)
    columns = output_df.columns
    if "meta" not in columns:
        return output_df

    for index, row in output_df.iterrows():
        if isinstance(row["meta"], str) and row["meta"]:
            meta_value = row["meta"]
            # merge all values from row into <item>.<index>.<field> fields
            for column in columns:
                if row[column]:
                    column_parts = column.split(".")
                    if len(column_parts) != 3:
                        continue  # skipping columns which are not in the form <item>.<index>.<field>
                    print(f"{column_parts=}\n{meta_value=}")
                    column_parts[-1] = meta_value
                    meta_column_name = ".".join(column_parts)
                    output_df[meta_column_name] = row[column]
            output_df.drop(index=index, inplace=True)
        else:
            break

    return output_df


# Record = dict[str, float | str | "Record"]


def expand_record_lists(record: dict[str, str], separator='.'):
    # -> Record
    """
    Transform a flat csv row into a row containing lists of dictionaries
    For example, `field.123.subfield` will be transformed into a structure
    of shape     `field[123][subfield]`
    """
    output_record: dict = {}
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


def doc_print_df(df: pandas.DataFrame, name: str = 'dataframe:'):
    pandas.set_option('display.max_rows', 100)
    pandas.set_option('display.max_columns', 15)
    pandas.set_option('display.width', 120)

    print(f"input dataframe:\n```\n{df}\n```\n")
