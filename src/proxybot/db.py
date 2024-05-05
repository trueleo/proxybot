import sqlite3

_cursor = None

def setup_db():
    conn = sqlite3.connect('./forward.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS forwards(message_id int PRIMARY KEY, user_id int, dm_message_id int)
    ''')

    global _conn
    _conn = conn

def get_db():
    return _conn

