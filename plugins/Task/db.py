import time, sqlite3


class SqliteDB(object):
    def __init__(self, bot, plugin_dir):
        """
        Open the connection
        """
        self.conn = sqlite3.connect(
            bot.path_converter(plugin_dir + "Task/data.db"), check_same_thread=False
        )  # 只读模式加上uri=True
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self.cursor.execute(
            "CREATE TABLE IF NOT EXISTS data (id INTEGER PRIMARY KEY autoincrement, user_id TEXT, content TEXT, type TEXT, timestamp INTEGER)"
        )

    def __del__(self):
        """
        Close the connection
        """
        self.cursor.close()
        self.conn.commit()
        self.conn.close()

    def insert(self, user_id, content, type):
        """
        Insert
        """
        timestamp = int(time.time())
        self.cursor.execute(
            "INSERT INTO data (user_id, content, type, timestamp) VALUES (?,?,?,?)",
            (user_id, content, type, timestamp),
        )

        last_inserted_id = self.cursor.lastrowid
        if self.cursor.rowcount == 1:
            return last_inserted_id
        else:
            return False

    def find_type(self, type):
        """
        Select
        """
        self.cursor.execute("SELECT * FROM data WHERE type=? LIMIT 1", (type,))
        result = self.cursor.fetchall()

        if result:
            return result[0]
        else:
            return False

    def get_user_info(self, user_id):
        """
        Select
        """
        self.cursor.execute("SELECT * FROM data WHERE user_id=? LIMIT 1", (user_id))
        result = self.cursor.fetchall()

        if result:
            return result[0]
        else:
            return False

    def find(self, user_id, type):
        """
        Select
        """
        self.cursor.execute(
            "SELECT * FROM data WHERE user_id=? and type=? LIMIT 1", (user_id, type)
        )
        result = self.cursor.fetchall()

        if result:
            return result[0]
        else:
            return False

    def select(self, user_id, type):
        """
        Select
        """
        self.cursor.execute(
            "SELECT * FROM data WHERE user_id=? and type=?", (user_id, type)
        )
        result = self.cursor.fetchall()

        if result:
            return result
        else:
            return False

    def select_type_records(self, type):
        """
        Select
        """
        self.cursor.execute("SELECT * FROM data WHERE type=?", (type,))
        result = self.cursor.fetchall()

        if result:
            return result
        else:
            return False

    def delete(self, user_id, type):
        """
        Delete
        """
        self.cursor.execute(
            "DELETE FROM data WHERE user_id=? and type=?", (user_id, type)
        )

        if self.cursor.rowcount == 1:
            return True
        else:
            return False

    def delete_id(self, id):
        """
        Delete
        """
        self.cursor.execute("DELETE FROM data WHERE id=?", (int(id),))

        if self.cursor.rowcount == 1:
            return True
        else:
            return False

    def delete_content(self, user_id, type, content):
        """
        Delete
        """
        self.cursor.execute(
            "DELETE FROM data WHERE user_id=? and type=? and content=?",
            (user_id, type, content),
        )

        if self.cursor.rowcount == 1:
            return True
        else:
            return False

    def update(self, user_id, type, content):
        """
        Insert
        """
        timestamp = int(time.time())
        self.cursor.execute(
            "UPDATE data Set content = ?,timestamp = ? WHERE user_id=? and type=?",
            (content, timestamp, user_id, type),
        )

        last_inserted_id = self.cursor.lastrowid
        if self.cursor.rowcount == 1:
            return last_inserted_id
        else:
            return False

    def update_id(self, id, content):
        """
        Insert
        """
        timestamp = int(time.time())
        self.cursor.execute(
            "UPDATE data Set content = ?,timestamp = ? WHERE id=?",
            (content, timestamp, id),
        )

        last_inserted_id = self.cursor.lastrowid
        if self.cursor.rowcount == 1:
            return last_inserted_id
        else:
            return False

    def update_type(self, type, content):
        """
        Insert
        """
        timestamp = int(time.time())
        self.cursor.execute(
            "UPDATE data Set content = ?,timestamp = ? WHERE type=?",
            (content, timestamp, type),
        )

        last_inserted_id = self.cursor.lastrowid
        if self.cursor.rowcount == 1:
            return last_inserted_id
        else:
            return False

    def insert_or_update(self, user_id, content, type):
        if self.find(user_id, type):
            return self.update(user_id, type, content)
        else:
            return self.insert(user_id, content, type)
