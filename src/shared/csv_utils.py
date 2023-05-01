import pandas


def process_csv_with_metadata(input_df: pandas.DataFrame) -> pandas.DataFrame:
    output_df = input_df.copy(deep=True)

    columns = output_df.columns
    for index, row in output_df.iterrows():
        if row["meta"]:
            meta_value = row["meta"]
            print(f"{row=}")
            # merge all values from row into <item>.<index>.<field> fields
            print(f"bef {output_df}")
            for column in columns:
                if row[column]:
                    column_parts = column.split(".")
                    if len(column_parts) != 3:
                        continue  # skipping columns which are not in the form <item>.<index>.<field>

                    meta_column_name = ".".join(column_parts[:-1] + [meta_value])
                    output_df[meta_column_name] = row[column]
                    print(f"aft {output_df}")
            output_df.drop(index=index, inplace=True)
        else:
            break

    return output_df
