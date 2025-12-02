# System/sqlite.py
import os
import sqlite3
from pathlib import Path
from typing import List, Optional, Any, Dict

BASE_DIR = Path(__file__).resolve().parents[3]

DB_PATH = os.environ.get(
    "OFFICESUD_DB_PATH",
    str(BASE_DIR / "officesud_db" / "db.sqlite3"),
)
db_path = DB_PATH


def check_and_initialize_db() -> bool:
    """
    Гарантируем, что файл БД и таблица Cases существуют.
    Существующую БД НЕ трогаем.
    """
    if not os.path.exists(db_path):
        initialize_db()   # создаём БД и таблицу
    else:
        # на всякий случай создадим таблицу, если её нет
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS Cases (
                DB_Case_ID INTEGER PRIMARY KEY AUTOINCREMENT,
                BatchID TEXT,
                InternalID TEXT,
                TalonID TEXT,
                PlaintiffName TEXT,
                PlaintiffID TEXT,
                PlaintiffSide TEXT,
                PlaintiffType TEXT,
                PlaintiffAddress TEXT,
                PlaintiffPhone TEXT,
                PlaintiffEmail TEXT,
                PlaintiffBank TEXT,
                DefendantName TEXT,
                DefendantID TEXT,
                DefendantSide TEXT,
                DefendantType TEXT,
                DefendantAddress TEXT,
                DefendantPhone TEXT,
                DefendantEmail TEXT,
                DefendantBank TEXT,
                RepName TEXT,
                RepID TEXT,
                RepSide TEXT,
                RepType TEXT,
                RepAddress TEXT,
                RepPhone TEXT,
                RepEmail TEXT,
                RepBank TEXT,
                ClaimAmount REAL,
                StateDuty REAL,
                ClaimSummary TEXT,
                ClaimBasis TEXT,
                RegionID TEXT,
                CourtID TEXT,
                PaymentDocPath TEXT,
                MainDocPath TEXT,
                OtherDocPath TEXT
            )
            """
        )
        conn.commit()
        conn.close()
    return True


def initialize_db(recreate: bool = False):
    """Создаём БД и таблицу Cases с нуля, НИЧЕГО не удаляя снаружи."""
    # ВАЖНО: не удаляем существующий файл, чтобы не ловить Permission denied
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS Cases (
            DB_Case_ID INTEGER PRIMARY KEY AUTOINCREMENT,
            BatchID TEXT,
            InternalID TEXT,
            TalonID TEXT,
            PlaintiffName TEXT,
            PlaintiffID TEXT,
            PlaintiffSide TEXT,
            PlaintiffType TEXT,
            PlaintiffAddress TEXT,
            PlaintiffPhone TEXT,
            PlaintiffEmail TEXT,
            PlaintiffBank TEXT,
            DefendantName TEXT,
            DefendantID TEXT,
            DefendantSide TEXT,
            DefendantType TEXT,
            DefendantAddress TEXT,
            DefendantPhone TEXT,
            DefendantEmail TEXT,
            DefendantBank TEXT,
            RepName TEXT,
            RepID TEXT,
            RepSide TEXT,
            RepType TEXT,
            RepAddress TEXT,
            RepPhone TEXT,
            RepEmail TEXT,
            RepBank TEXT,
            ClaimAmount REAL,
            StateDuty REAL,
            ClaimSummary TEXT,
            ClaimBasis TEXT,
            RegionID TEXT,
            CourtID TEXT,
            PaymentDocPath TEXT,
            MainDocPath TEXT,
            OtherDocPath TEXT
        )
        """
    )
    conn.commit()
    conn.close()

def get_case_participants(batch_id: str) -> List[Dict[str, Any]]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT *
        FROM Cases
        WHERE BatchID = ?
    """, (batch_id,))
    
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def get_unique_internal_ids(batch_id: str) -> List[str]:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT InternalID
        FROM Cases
        WHERE BatchID = ?
    """, (batch_id,))
    ids = [row[0] for row in cursor.fetchall()]
    conn.close()
    return ids

def get_case_data_by_internal_id(internal_id: str) -> Optional[Dict[str, Any]]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT *
        FROM Cases
        WHERE InternalID = ?
        LIMIT 1
    """, (internal_id,))
    
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return dict(row)
    return None

def update_case_status(internal_id: str, talon_id: str):

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE Cases
        SET TalonID = ?
        WHERE InternalID = ?
    """, (talon_id, internal_id))
    conn.commit()
    conn.close()


def get_batch_progress(batch_id):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM cases WHERE BatchID = ?", (batch_id,))
    total_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM cases WHERE BatchID = ? AND TalonID IS NOT NULL AND TalonID != ''", (batch_id,))
    processed_count = cursor.fetchone()[0]
    
    conn.close()
    return processed_count, total_count