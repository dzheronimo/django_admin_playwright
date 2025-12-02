import sqlite3
import pandas as pd
import uuid
from datetime import datetime
from typing import List, Dict, Any

from application.officesud.System import sqlite as office_sqlite

DB_PATH = office_sqlite.DB_PATH  # или office_sqlite.db_path

def load_excel_to_db(excel_file_path): 
    office_sqlite.check_and_initialize_db()
    batch_id = f"BATCH-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"
    df = pd.read_excel(excel_file_path, dtype=str) 
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("PRAGMA table_info(Cases);")
    valid_columns = [col[1] for col in cursor.fetchall()]

    df = df[[col for col in df.columns if col in valid_columns]]
    for _, row in df.iterrows():
        data = row.to_dict()
        data["BatchID"] = batch_id
        columns = ', '.join(f'"{col}"' for col in data.keys())
        placeholders = ', '.join('?' for _ in data)
        values = list(data.values())
        try:
            cursor.execute(f"INSERT INTO Cases ({columns}) VALUES ({placeholders})", values)
        except sqlite3.OperationalError as e:
            print(f"Ошибка выполнения SQL: {e}")
            print("Убедитесь, что заголовки столбцов в Excel совпадают с полями таблицы Cases.")
            conn.close()
            raise
    conn.commit()
    conn.close()
    print(f"Данные из {excel_file_path} загружены в базу. BatchID: {batch_id}")
    return batch_id

def write_data_to_excel(data: List[Dict[str, Any]], output_file_path: str):
    df = pd.DataFrame(data)
    columns_to_drop = []
    if 'DB_Case_ID' in df.columns:
        columns_to_drop.append('DB_Case_ID')
    if 'BatchID' in df.columns:
        columns_to_drop.append('BatchID')
    if columns_to_drop:
        df = df.drop(columns=columns_to_drop, errors='ignore') 
    try:
        with pd.ExcelWriter(output_file_path, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Экспорт_Пакет', index=False)
    except Exception as e:
        raise