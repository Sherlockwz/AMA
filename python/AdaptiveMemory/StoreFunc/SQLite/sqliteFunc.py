from __future__ import annotations

import sqlite3
import os
import json
import re
from datetime import datetime

_DATA_DIR = "Store"


def set_data_dir(data_dir: str | None):
    global _DATA_DIR
    if data_dir:
        _DATA_DIR = os.path.abspath(data_dir)


def get_data_dir() -> str:
    os.makedirs(_DATA_DIR, exist_ok=True)
    return _DATA_DIR


def get_db_path() -> str:
    return os.path.join(get_data_dir(), "AMA.db")


def normalize_table_name(name: str) -> str:
    normalized = re.sub(r"[^0-9A-Za-z_]", "_", name.strip())
    normalized = re.sub(r"_+", "_", normalized).strip("_")
    if not normalized:
        normalized = "user"
    if normalized[0].isdigit():
        normalized = f"user_{normalized}"
    return normalized

def createDb():
    os.makedirs(get_data_dir(), exist_ok=True)
    conn = sqlite3.connect(get_db_path())
    print("✅ Database created or connected successfully: AMA.db")
    conn.close()

def createTable(user: str):
    conn = sqlite3.connect(get_db_path(), timeout=10)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?;", (user,)
    )
    tableExists = cursor.fetchone()

    if tableExists:
        print(f"⚠️ Table '{user}' already exists in Store/AMA.db")
    else:
        cursor.execute(f'''
            CREATE TABLE {user} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT,
                fact TEXT,
                source TEXT,
                related_id TEXT,
                dia_id TEXT,
                timestamp TEXT,
                episode INTEGER,
                meta TEXT
            );
        ''')
        conn.commit()
        print(f"✅ Table '{user}' created successfully in Store/AMA.db")

    conn.close()

def createTableEpisode(user: str):
    conn = sqlite3.connect(get_db_path(), timeout=10)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?;", (user,)
    )
    tableExists = cursor.fetchone()

    if tableExists:
        print(f"⚠️ Table '{user}' already exists in Store/AMA.db")
    else:
        cursor.execute(f'''
            CREATE TABLE {user} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT,
                meta TEXT
            );
        ''')
        conn.commit()
        print(f"✅ Table '{user}' created successfully in Store/AMA.db")

    conn.close()

def insertRecordEpisode(
    user: str,
    content: str,
    meta: str = None,
):
    conn = sqlite3.connect(get_db_path(), timeout=10)
    cursor = conn.cursor()

    cursor.execute(f'''
        INSERT INTO {user} (content, meta)
        VALUES (?, ?);
    ''', (content, meta))

    conn.commit()
    recordId = cursor.lastrowid
    print(f"✅ Record inserted successfully into '{user}' with id={recordId}")
    conn.close()

    return recordId

def createSentenceTable(name: str):
    conn = sqlite3.connect(get_db_path(), timeout=10)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?;", (name,)
    )
    tableExists = cursor.fetchone()

    if tableExists:
        print(f"⚠️ Table '{name}' already exists in Store/AMA.db")
    else:
        cursor.execute(f'''
            CREATE TABLE {name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT,
                episodeID INTEGER
            );
        ''')

        conn.commit()
        print(f"✅ Table '{name}' created successfully in Store/AMA.db")

    conn.close()

def createFactKnowledgeTable(name: str):
    conn = sqlite3.connect(get_db_path(), timeout=10)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?;", (name,)
    )
    tableExists = cursor.fetchone()

    if tableExists:
        print(f"⚠️ Table '{name}' already exists in Store/AMA.db")
    else:
        cursor.execute(f'''
            CREATE TABLE {name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT,
                diaNO INTEGER,
                dia_id TEXT,
                timestamp TEXT,
                meta TEXT
            );
        ''')
        conn.commit()
        print(f"✅ Table '{name}' created successfully in Store/AMA.db")

    conn.close()

def insertRecord(
    user: str,
    content: str,
    fact: str = None,
    source: str = "user",
    related_id=None,
    dia_id: str = None,
    timestamp: str = None,
    meta: str = None,
):
    if timestamp is None or timestamp == "empty":
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if isinstance(related_id, list):
        related_id = json.dumps(related_id)

    conn = sqlite3.connect(get_db_path(), timeout=10)
    cursor = conn.cursor()

    cursor.execute(f'''
        INSERT INTO {user} (content, fact, source, related_id, dia_id, timestamp, meta)
        VALUES (?, ?, ?, ?, ?, ?, ?);
    ''', (content, fact, source, related_id, dia_id, timestamp, meta))

    conn.commit()
    recordId = cursor.lastrowid
    print(f"✅ Record inserted successfully into '{user}' with id={recordId}")
    conn.close()

    return recordId

def insertFactRecord(
    name: str,
    id: int = None,
    content: str = None,
    diaNO: int = None,
    dia_id: str = None,
    timestamp: str = None,
    meta: str = None,
):
    if timestamp is None or timestamp == "empty":
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = sqlite3.connect(get_db_path(), timeout=10)
    cursor = conn.cursor()

    if id is not None:
        cursor.execute(f'''
            INSERT INTO {name} (id, content, diaNO, dia_id, timestamp, meta)
            VALUES (?, ?, ?, ?, ?, ?);
        ''', (id, content, diaNO, dia_id, timestamp, meta))
    else:
        cursor.execute(f'''
            INSERT INTO {name} (content, diaNO, dia_id, timestamp)
            VALUES (?, ?, ?, ?);
        ''', (content, diaNO, dia_id, timestamp))

    conn.commit()
    recordId = cursor.lastrowid if id is None else id
    print(f"✅ Record inserted successfully into '{name}' with id={recordId}")
    conn.close()

    return recordId

def insertBatchRecords(user: str, data: list[dict]):
    if not data:
        print("⚠️ No data to insert.")
        return []

    conn = sqlite3.connect(get_db_path(), timeout=10)
    cursor = conn.cursor()

    inserted_ids = []

    for entry in data:
        content = entry.get("content", "")
        fact = entry.get("fact")
        source = entry.get("source", "user")
        related_id = entry.get("related_id")
        dia_id = entry.get("dia_id")
        timestamp = entry.get("timestamp")
        meta = entry.get("meta")

        if timestamp is None or timestamp == "empty":
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if isinstance(related_id, list):
            related_id = json.dumps(related_id)

        cursor.execute(f'''
            INSERT INTO {user} (content, fact, source, related_id, dia_id, timestamp, meta)
            VALUES (?, ?, ?, ?, ?, ?, ?);
        ''', (content, fact, source, related_id, dia_id, timestamp, meta))

        inserted_ids.append(cursor.lastrowid)

    conn.commit()
    conn.close()

    print(f"✅ Successfully inserted {len(inserted_ids)} records into '{user}'.")
    return inserted_ids

def insertFactRecordsBatch(name: str, data: list[dict]):
    if not data:
        print("⚠️ No data provided — nothing to insert.")
        return []

    conn = sqlite3.connect(get_db_path(), timeout=10)
    cursor = conn.cursor()

    inserted_ids = []

    for entry in data:
        content = entry.get("content")
        diaNO = entry.get("diaNO")
        dia_id = entry.get("dia_id")
        timestamp = entry.get("timestamp")
        meta = entry.get("meta","")

        if not timestamp or timestamp == "empty":
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute(f'''
            INSERT INTO {name} (content, diaNO, dia_id, timestamp, meta)
            VALUES (?, ?, ?, ?, ?);
        ''', (content, diaNO, dia_id, timestamp, meta))

        inserted_ids.append(cursor.lastrowid)

    conn.commit()
    conn.close()

    print(f"✅ Successfully inserted {len(inserted_ids)} record(s) into '{name}'.")
    return inserted_ids

def queryById(user: str, recordId: int):
    conn = sqlite3.connect(get_db_path(), timeout=10)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(f"SELECT * FROM {user} WHERE id = ?;", (recordId,))
    row = cursor.fetchone()

    if row:
        record = dict(row)

        if record.get("related_id"):
            try:
                record["related_id"] = json.loads(record["related_id"])
            except Exception:
                pass

        conn.close()
        return record
    else:
        conn.close()
        return None

def queryMetaFromId(user: str, recordId: int) -> str | None:
    conn = sqlite3.connect(get_db_path(), timeout=10)
    cursor = conn.cursor()

    cursor.execute(f"SELECT meta FROM {user} WHERE id = ?;", (recordId,))
    result = cursor.fetchone()

    conn.close()

    if result and result[0] is not None:
        return result[0]
    else:
        print(f"⚠️ No meta found for id={recordId} in table '{user}'.")
        return None

def queryByIdList(user: str, idList: list[int]):
    if not idList:
        print("⚠️ ID list is empty — nothing to query.")
        return []

    conn = sqlite3.connect(get_db_path(), timeout=10)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    placeholders = ','.join(['?'] * len(idList))
    order_case = ' '.join([f"WHEN {id} THEN {i}" for i, id in enumerate(idList)])
    query = f"""
        SELECT * FROM {user}
        WHERE id IN ({placeholders})
        ORDER BY CASE id {order_case} END;
    """

    cursor.execute(query, idList)
    rows = cursor.fetchall()

    results = []
    for row in rows:
        record = dict(row)
        if record.get("related_id"):
            try:
                record["related_id"] = json.loads(record["related_id"])
            except Exception:
                pass
        results.append(record)

    conn.close()

    if results:
        print(f"✅ Fetched {len(results)} records from '{user}' in original order.")
    else:
        print(f"⚠️ No records found in table '{user}' for given IDs.")

    return results

def deleteRecordsByIdList(user: str, idList: list[int]):
    if not idList:
        print("⚠️ ID list is empty — nothing to delete.")
        return "ID list is empty"

    conn = sqlite3.connect(get_db_path(), timeout=10)
    cursor = conn.cursor()

    placeholders = ", ".join(["?"] * len(idList))

    cursor.execute(f"DELETE FROM {user} WHERE id IN ({placeholders});", idList)
    deletedCount = cursor.rowcount

    conn.commit()
    conn.close()

    if deletedCount > 0:
        msg = f"✅ Deleted {deletedCount} record(s) from '{user}'."
        print(msg)
        return msg
    else:
        msg = "⚠️ No matching records found."
        print(msg)
        return msg

def queryAllUsers():
    conn = sqlite3.connect(get_db_path(), timeout=10)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type='table'
          AND name NOT LIKE 'sqlite_%'
        ORDER BY name COLLATE NOCASE;
    """)
    tables = [row[0] for row in cursor.fetchall()]

    if tables:
        print("✅ Existing users (tables) in Store/AMA.db:")
        for t in tables:
            print(f"   - {t}")
    else:
        print("⚠️ No user tables found in Store/AMA.db")

    conn.close()

    return tables

def deleteUser(user: str):
    conn = sqlite3.connect(get_db_path(), timeout=10)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?;", (user,)
    )
    exists = cursor.fetchone()

    if exists:
        cursor.execute(f"DROP TABLE {user};")
        conn.commit()
        print(f"🗑️ Table '{user}' has been deleted successfully from Store/AMA.db.")
    else:
        print(f"⚠️ Table '{user}' does not exist in Store/AMA.db.")

    conn.close()

def deleteAllUsers():
    tables = queryAllUsers()

    if not tables:
        print("⚠️ No user tables found in Store/AMA.db — nothing to delete.")
        return

    conn = sqlite3.connect(get_db_path(), timeout=10)
    cursor = conn.cursor()

    for table in tables:
        cursor.execute(f"DROP TABLE IF EXISTS {table};")
        print(f"🗑️ Table '{table}' deleted successfully.")

    conn.commit()
    conn.close()
    print("✅ All user tables have been deleted from Store/AMA.db.")

def deleteTable(tableName: str):
    conn = sqlite3.connect(get_db_path(), timeout=10)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?;",
        (tableName,)
    )
    exists = cursor.fetchone()

    if not exists:
        print(f"⚠️ Table '{tableName}' does not exist in Store/AMA.db.")
        conn.close()
        return False

    cursor.execute(f"DROP TABLE {tableName};")
    conn.commit()
    conn.close()

    print(f"💀 Table '{tableName}' has been permanently deleted from Store/AMA.db.")
    return True

def queryLastRecord(user: str):
    conn = sqlite3.connect(get_db_path(), timeout=10)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(f"SELECT * FROM {user} ORDER BY id DESC LIMIT 1;")
    row = cursor.fetchone()

    if row:
        record = dict(row)
        if record.get("related_id"):
            try:
                record["related_id"] = json.loads(record["related_id"])
            except Exception:
                pass

        conn.close()
        return record
    else:
        conn.close()
        return None

def clearTable(user: str):
    conn = sqlite3.connect(get_db_path(), timeout=10)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?;", (user,)
    )
    exists = cursor.fetchone()

    if exists:
        cursor.execute(f"DELETE FROM {user};")
        conn.commit()
        print(f"🧹 All records in table '{user}' have been deleted (structure preserved).")
    else:
        print(f"⚠️ Table '{user}' does not exist in Store/AMA.db.")

    conn.close()

def updateRecord(
    user: str,
    recordId: int,
    content: str = None,
    fact: str = None,
    source: str = None,
    related_id=None,
    dia_id: str = None,
    timestamp: str = None,
    meta: str = None,
):
    conn = sqlite3.connect(get_db_path(), timeout=10)
    cursor = conn.cursor()

    cursor.execute(f"SELECT * FROM {user} WHERE id = ?;", (recordId,))
    record = cursor.fetchone()
    if not record:
        print(f"⚠️ No record found with id={recordId} in table '{user}'.")
        conn.close()
        return False

    updates = {}
    if content is not None:
        updates["content"] = content
    if fact is not None:
        updates["fact"] = fact
    if source is not None:
        updates["source"] = source
    if related_id is not None:
        if isinstance(related_id, list):
            related_id = json.dumps(related_id)
        updates["related_id"] = related_id
    if dia_id is not None:
        updates["dia_id"] = dia_id
    if meta is not None:
        updates["meta"] = meta

    if timestamp is None or timestamp == "empty":
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    updates["timestamp"] = timestamp

    if not updates:
        print("⚠️ No fields provided to update.")
        conn.close()
        return False

    setClause = ", ".join([f"{k} = ?" for k in updates.keys()])
    values = list(updates.values()) + [recordId]

    cursor.execute(f"UPDATE {user} SET {setClause} WHERE id = ?;", values)
    conn.commit()
    conn.close()

    print(f"✅ Record with id={recordId} in table '{user}' has been updated.")
    return True

def updateMetaOnly(user: str, recordId: int, new_meta: str):
    conn = sqlite3.connect(get_db_path(), timeout=10)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(f"SELECT meta FROM {user} WHERE id = ?;", (recordId,))
    row = cursor.fetchone()
    if not row:
        print(f"⚠️ No record found with id={recordId} in table '{user}'.")
        conn.close()
        return False

    old_meta = row["meta"] if row["meta"] else ""
    
    combined_meta = f"{old_meta}{new_meta}\n" if old_meta else f"{new_meta}\n"

    cursor.execute(
        f"UPDATE {user} SET meta = ? WHERE id = ?;",
        (combined_meta, recordId),
    )

    conn.commit()
    conn.close()

    print(f"✅ Appended new meta for record id={recordId} in table '{user}'.")
    return True

def updateFactRecords(name: str, data: list[dict]):
    if not data:
        print("⚠️ Empty data list — nothing to update.")
        return 0

    conn = sqlite3.connect(get_db_path(), timeout=10)
    cursor = conn.cursor()
    updatedCount = 0

    for entry in data:
        recordId = entry.get("id")
        if not recordId:
            print("⚠️ Skipping entry without 'id'.")
            continue

        cursor.execute(f"SELECT * FROM {name} WHERE id = ?;", (recordId,))
        if not cursor.fetchone():
            print(f"⚠️ No record found with id={recordId} in '{name}'. Skipped.")
            continue

        updates = {}
        if "content" in entry and entry["content"] is not None:
            updates["content"] = entry["content"]
        if "diaNO" in entry and entry["diaNO"] is not None:
            updates["diaNO"] = entry["diaNO"]
        if "dia_id" in entry and entry["dia_id"] is not None:
            updates["dia_id"] = entry["dia_id"]
        if "timestamp" in entry:
            ts = entry["timestamp"]
            if ts is None or ts == "empty":
                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            updates["timestamp"] = ts
        else:
            updates["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if not updates:
            print(f"⚠️ No updatable fields for id={recordId}. Skipped.")
            continue

        setClause = ", ".join([f"{k} = ?" for k in updates.keys()])
        values = list(updates.values()) + [recordId]

        cursor.execute(f"UPDATE {name} SET {setClause} WHERE id = ?;", values)
        updatedCount += 1

    conn.commit()
    conn.close()

    print(f"✅ Successfully updated {updatedCount} record(s) in '{name}'.")
    return updatedCount

def queryByDiaId(user: str, diaIds):
    conn = sqlite3.connect(get_db_path(), timeout=10)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if isinstance(diaIds, str):
        cursor.execute(f"SELECT * FROM {user} WHERE dia_id = ?;", (diaIds,))
        row = cursor.fetchone()

        if row:
            record = dict(row)
            if record.get("related_id"):
                try:
                    record["related_id"] = json.loads(record["related_id"])
                except Exception:
                    pass
            conn.close()
            return record
        else:
            conn.close()
            print(f"⚠️ No record found in '{user}' for dia_id={diaIds}.")
            return None

    elif isinstance(diaIds, list) and diaIds:
        placeholders = ','.join(['?'] * len(diaIds))
        order_case = ' '.join([f"WHEN '{d}' THEN {i}" for i, d in enumerate(diaIds)])
        query = f"""
            SELECT * FROM {user}
            WHERE dia_id IN ({placeholders})
            ORDER BY CASE dia_id {order_case} END;
        """
        cursor.execute(query, diaIds)
        rows = cursor.fetchall()

        results = []
        for row in rows:
            record = dict(row)
            if record.get("related_id"):
                try:
                    record["related_id"] = json.loads(record["related_id"])
                except Exception:
                    pass
            results.append(record)

        conn.close()

        if results:
            print(f"✅ Fetched {len(results)} records from '{user}' by dia_id list.")
            return results
        else:
            print(f"⚠️ No records found in '{user}' for given dia_id list.")
            return None

    else:
        conn.close()
        print("⚠️ diaIds must be a non-empty string or list.")
        return None
