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

    
    if result:
        desc = ""
        i=0
        for table_index, table_name in enumerate(table_names_original):
            desc=desc+table_name+'('
            for column_index, column_value in enumerate(column_names_original):
                isp = ""
                if column_value[0]==table_index:
                    if column_index in primarys:
                        isp = " PRIMARY KEY"
                    else:
                        isp = ""
                    desc=desc+column_value[1]+':'+column_names[column_index][1]+' type:'+column_types[column_index]+isp+'|'
                    i=i+1
            desc=desc+')\n'
        return desc
    else:
        return " none "
