import os
import sqlite3
import threading

import cfg

DB_NAME = "state.db"

DB_SCHEMA = [
    "CREATE TABLE IF NOT EXISTS log ("
    " id INTEGER PRIMARY KEY AUTOINCREMENT,"
    " ts INTEGER NOT NULL,"
    " lvl TEXT NOT NULL,"
    " tag TEXT NOT NULL,"
    " msg TEXT NOT NULL)",
    "CREATE INDEX IF NOT EXISTS log_id_idx ON log (id DESC)",
    "CREATE TABLE IF NOT EXISTS kv ("
    " k TEXT PRIMARY KEY,"
    " v TEXT NOT NULL,"
    " ts INTEGER NOT NULL)"
]

DB_H = None
DB_LK = threading.Lock()


def db_path():
    return os.path.join(cfg.cfg_home(), DB_NAME)


def db_open():
    global DB_H
    if DB_H != None:
        return DB_H
    if cfg.cfg_mkhome() != 0:
        return None
    try:
        h = sqlite3.connect(db_path(), check_same_thread=False)
    except sqlite3.Error:
        return None
    try:
        h.execute("PRAGMA journal_mode=WAL")
        h.execute("PRAGMA busy_timeout=4000")
        i = 0
        while i < len(DB_SCHEMA):
            h.execute(DB_SCHEMA[i])
            i = i + 1
        h.commit()
    except sqlite3.Error:
        h.close()
        return None
    DB_H = h
    return DB_H


def db_close():
    global DB_H
    if DB_H == None:
        return
    DB_LK.acquire()
    try:
        DB_H.close()
    except sqlite3.Error:
        pass
    DB_H = None
    DB_LK.release()


def db_exec(sql, args):
    h = db_open()
    if h == None:
        return -1
    DB_LK.acquire()
    rc = 0
    try:
        h.execute(sql, args)
        h.commit()
    except sqlite3.Error:
        rc = -1
    DB_LK.release()
    return rc


def db_query(sql, args):
    h = db_open()
    if h == None:
        return None
    DB_LK.acquire()
    rows = None
    try:
        cur = h.execute(sql, args)
        rows = cur.fetchall()
        cur.close()
    except sqlite3.Error:
        rows = None
    DB_LK.release()
    return rows


def db_one(sql, args):
    rows = db_query(sql, args)
    if rows == None:
        return None
    if len(rows) == 0:
        return None
    return rows[0]


def kv_set(k, v, ts):
    sql = ("INSERT INTO kv (k, v, ts) VALUES (?, ?, ?)"
           " ON CONFLICT(k) DO UPDATE SET v = ?, ts = ?")
    return db_exec(sql, (k, v, ts, v, ts))


def kv_get(k):
    row = db_one("SELECT v FROM kv WHERE k = ?", (k,))
    if row == None:
        return None
    return row[0]


def kv_del(k):
    return db_exec("DELETE FROM kv WHERE k = ?", (k,))


def db_count(tab):
    row = db_one("SELECT COUNT(*) FROM " + tab, ())
    if row == None:
        return -1
    return row[0]
