import os
import pandas as pd
import json

def db_getdesc(dbname):
    # description path
    filepath = 'datasets/cosql_dataset/tables.json'

    with open(filepath, 'r', encoding='utf-8') as file:
        data = json.load(file)
    
    result = [item for item in data if 'db_id' in item and item['db_id'] == dbname]

    table_names_original = result[0]['table_names_original']
    column_names_original = result[0]['column_names_original']
    column_names = result[0]['column_names']    
    column_types = result[0]['column_types'] 
    primarys = result[0]['primary_keys']
    foreign_keys = result[0]["foreign_keys"]

    columns_selected = []
    if result:
        desc = ""
        i=0
        for table_index, table_name in enumerate(table_names_original):
            desc=desc+table_name+'('
            for column_index, column_value in enumerate(column_names_original):
                columns_selected.append(column_index)
                isp = ""
                if column_value[0]==table_index:
                    if column_index in primarys:
                        isp = " PRIMARY KEY"
                    else:
                        isp = ""
                    desc=desc+column_value[1]+':'+column_names[column_index][1]+' type:'+column_types[column_index]+isp+'|'
                    i=i+1
            desc=desc+')\n'


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
            text = " = ".join([f"{item[0]}.{item[1]}" for item in sublist])
            FK_output += text + "\n"
        desc = desc + FK_output
        return desc
    else:
        return " none "
