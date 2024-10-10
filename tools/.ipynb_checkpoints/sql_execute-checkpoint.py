import sqlite3
import time

def sqlite_execute(dbname, sql):
    # connect SQLite
    conn = sqlite3.connect(dbname)
    
    cursor = conn.cursor()
    
    try:
        start_time = time.time()
        cursor.execute(sql)
        conn.commit()
        end_time = time.time()
        query_time = end_time - start_time
        result = cursor.fetchall()
        return result[:10], query_time, True
        
    except sqlite3.Error as e:
        return [], 0.0, False
        
    finally:
        conn.close()


def sqlite_execute_with_log(dbname, sql):
    # connect SQLite
    conn = sqlite3.connect(dbname)
    
    cursor = conn.cursor()
    
    try:
        start_time = time.time()
        cursor.execute(sql)
        conn.commit()
        end_time = time.time()
        query_time = end_time - start_time
        result = cursor.fetchall()
        return result[:10], query_time, True, ""
        
    except sqlite3.Error as e:
        return [], 0.0, False, str(e)
        
    finally:
        conn.close()
