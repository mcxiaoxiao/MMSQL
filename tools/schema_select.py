from tools.sql_execute import sqlite_execute as execute
import os
import pandas as pd
import json


def sql_evoke(query, db_name):
    result, execution_time, executable = execute(
        "datasets/cosql_dataset/database/" + db_name + "/" + db_name + ".sqlite",
        query,
    )
    return result


def schema_select(dbname, table_config):
    """
    Retrieves the database description, filtering tables and columns
    based on the provided configuration.

    Args:
        dbname (str): The name of the database.
        table_config (dict): A dictionary specifying which tables and
                             columns to keep or drop. Keys are table names,
                             values are either:
                                - "drop_all" to drop the entire table,
                                - "keep_all" to keep the entire table, or
                                - a list of column names to keep.

    Returns:
        str: The formatted database description with the selected tables
             and columns, including example data.
    """

    filepath = "datasets/cosql_dataset/tables.json"

    with open(filepath, "r", encoding="utf-8") as file:
        data = json.load(file)

    result = [item for item in data if "db_id" in item and item["db_id"] == dbname]

    if not result:
        return " none "

    table_names_original = result[0]["table_names_original"]
    column_names_original = result[0]["column_names_original"]
    column_names = result[0]["column_names"]
    column_types = result[0]["column_types"]
    primarys = result[0]["primary_keys"]
    foreign_keys = result[0]["foreign_keys"]

    desc = ""
    columns_selected = []
    for table_index, table_name in enumerate(table_names_original):

        
        
        if table_name in table_config:
            
            if table_config[table_name] == "drop_all":
                continue

            desc += "Table:" + table_name + "\n["

            for column_index, column_value in enumerate(column_names_original):

                if (column_value[0] == table_index
                    and (table_config[table_name] == "keep_all"
                    or (isinstance(table_config[table_name], dict) and (table_config[table_name].get('keep_all') == "keep_all" or table_config[table_name].get('keep_all') == True))
                    or column_value[1] in table_config[table_name]
                    )):
                    isp = " PRIMARY KEY" if column_index in primarys else ""
                    
                    sql_get_eg = f"SELECT DISTINCT {column_value[1]} FROM {table_name} LIMIT 3;"
                    examples_raw = sql_evoke(sql_get_eg, dbname)
                    examples = ", ".join([str(row[0]) for row in examples_raw])
                    columns_selected.append(column_index)
                    desc += (
                        '(\''
                        + column_value[1]
                        + "\', "
                        + column_names[column_index][1]
                        + " type:"
                        + column_types[column_index]
                        + isp
                        + ". Value examples:["
                        + examples
                        + "]),"
                    )

            desc = desc.rstrip("|") + "]\n"
            
    # print(foreign_keys,columns_selected)
    matching_sublists = [
        sublist for sublist in foreign_keys if sum(item in columns_selected for item in sublist) == 2
    ]
    column_names_selected = [[column_names_original[i] for i in sublist] for sublist in matching_sublists]
    result = []
    for sublist in column_names_selected:
        new_sublist = [[table_names_original[item[0]], item[1]] for item in sublist]
        result.append(new_sublist)
    FK_output = "Foreign keys:\n"
    for sublist in result:
        text = " = ".join([f"{item[0]}.'{item[1]}'" for item in sublist])
        FK_output += text + "\n"
    desc = desc + FK_output
    return desc
