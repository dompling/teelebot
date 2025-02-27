# -*- coding:utf-8 -*-
import os, json, re, time, sqlite3
from .quark_auto_save import Quarks, do_save, verify_account

data_db_type = {
    "cookie": "cookie",
    "path": "path",
    "auto_save": "auto_save",
    "admin": "admin",
    "rec_pwd": "rec_pwd",
    "super_admin": "super_admin",
}


class SqliteDB(object):
    def __init__(self, bot, plugin_dir):
        """
        Open the connection
        """
        self.conn = sqlite3.connect(
            bot.path_converter(plugin_dir + "Quark/data.db"), check_same_thread=False
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


def get_cookie(path):
    cookies = ""
    if os.path.exists(path):
        try:
            return open(path).read()
        except FileNotFoundError as e:
            return False
    return cookies


def save_cookie(path, cookies):
    with open(path, "w", encoding="utf-8") as file:
        # 将内容写入文件
        file.write(cookies)


prefix = "/qk"


def Quark(bot, message):
    plugin_dir = bot.plugin_dir
    db = SqliteDB(bot, plugin_dir)

    gap = 30
    message_id = message["message_id"]
    text = message.get("text", "")
    chat_id = message["chat"]["id"]
    user_id = message["from"]["id"]
    chat_type = message["chat"]["type"]
    bot_id = bot.bot_id

    super_admin = db.find_type(data_db_type["super_admin"])
    admin = db.find(user_id=user_id, type=data_db_type["admin"])

    is_admin = admin
    if is_admin == False and super_admin:
        is_admin = int(super_admin["user_id"]) == user_id

    if str(user_id) == bot_id:
        return

    if text.startswith(prefix):
        if super_admin == False and text.startswith(f"{prefix}admin"):
            return handle_admin_commands(bot, message, db, super_admin)

        if check_user_admin(bot, message, super_admin, is_admin) == False:
            return

        bot.message_deletor(gap, message["chat"]["id"], message_id)

        if text.startswith(f"{prefix}set"):
            cookies = text.split(f"{prefix}set ")[1]
            db.insert(user_id=user_id, content=cookies, type=data_db_type["cookie"])
            status = bot.sendMessage(
                text="✅ Cookies 保存成功",
                chat_id=chat_id,
                parse_mode="HTML",
                reply_to_message_id=message_id,
            )
            return bot.message_deletor(5, chat_id, status["message_id"])

        if text.startswith(f"{prefix}path"):
            path = text.split(f"{prefix}path ")[1]
            db.insert(user_id=user_id, content=path, type=data_db_type["path"])
            status = bot.sendMessage(
                text=f"✅ 默认分享链接保存路径为{path}",
                chat_id=chat_id,
                parse_mode="HTML",
                reply_to_message_id=message_id,
            )
            return bot.message_deletor(5, chat_id, status["message_id"])

    is_quark, uri = macth_content(json.dumps(message, ensure_ascii=False))
    if is_quark:
        save_path = db.find(user_id=user_id, type=data_db_type["path"])
        cookies = db.find(user_id=user_id, type=data_db_type["cookie"])

        if not cookies:
            status = bot.sendMessage(
                chat_id=message["chat"]["id"],
                text=f"请使用 {prefix}set 设置夸克 Cookie",
                parse_mode="HTML",
            )
            return bot.message_deletor(5, chat_id, status["message_id"])

        if not save_path:
            status = bot.sendMessage(
                chat_id=message["chat"]["id"],
                text=f"请使用 {prefix}path 设置夸克默认保存目录",
                parse_mode="HTML",
            )
            return bot.message_deletor(5, chat_id, status["message_id"])

        savepath = save_path["content"]
        cookie = cookies["content"]

        account = Quarks(cookie, 0)
        if not verify_account(account):
            status = bot.sendMessage(
                chat_id=message["chat"]["id"],
                text="🚫Cookie访问频繁，请更换或者稍后再试",
                parse_mode="HTML",
                reply_to_message_id=message_id,
            )
            return bot.message_deletor(20, chat_id, status["message_id"])

        task = {
            "taskname": "夸克机器人保存任务",
            "shareurl": uri,
            "savepath": savepath,
            "pattern": "",
            "replace": "",
            "enddate": "2099-01-30",
        }
        notify_body = do_save(account, [task])
        notify_body = "\n".join(notify_body)
        status = bot.sendMessage(
            chat_id=message["chat"]["id"],
            text=notify_body,
            parse_mode="HTML",
            reply_to_message_id=message_id,
        )
        return bot.message_deletor(20, chat_id, status["message_id"])


def macth_content(content):
    path = re.search(r"https:\/\/pan\.quark\.cn\/s\/([a-z0-9]+)", content)
    if path:
        return True, path.group(0)
    return False, content


def check_user_admin(bot, message, super_admin: bool, is_admin: bool):
    """
    是否是Bot管理员验证登录
    """
    chat_type = message["chat"]["type"]
    message_id = message["message_id"]
    chat_id = message["chat"]["id"]
    msg = ""
    if super_admin == False and chat_type != "private":
        msg = "🚫当前机器人暂无管理员\n请私聊执行<b>/qkadmin</b>"
    elif super_admin == False and chat_type == "private":
        msg = "🚫当前机器人暂无管理员\n请执行<b>/qkadmin</b>"
    elif is_admin == False:
        msg = "🚫您当前暂无机器人管理权限\n请私聊管理员获取"
    if msg:
        status = bot.sendMessage(
            text=msg,
            chat_id=chat_id,
            parse_mode="HTML",
            reply_to_message_id=message_id,
        )
        bot.message_deletor(5, chat_id, status["message_id"])
        return False
    return True


def handle_admin_commands(bot, message, db: SqliteDB, super_admin: bool):
    message_id = message["message_id"]
    chat_id = message["chat"]["id"]
    user_id = message["from"]["id"]
    chat_type = message["chat"]["type"]
    reply_to_message = message.get("reply_to_message", False)

    if super_admin == False and chat_type == "private":
        result = db.insert(
            user_id=user_id, type="super_admin", content=message["from"]["username"]
        )
        if result:
            msg = (
                "✅超级管理员初始化成功\n可引用消息，执行<b>/qkadmin</b>设置其他管理员"
            )
        else:
            msg = "🚫超级管理员初始化失败, 请重试"
        status = bot.sendMessage(
            text=msg,
            chat_id=chat_id,
            parse_mode="HTML",
            reply_to_message_id=message_id,
        )
        bot.message_deletor(5, chat_id, status["message_id"])

    elif reply_to_message:
        user_id = reply_to_message["from"]["id"]
        user_name = reply_to_message["from"]["username"]
        result = db.find(user_id=user_id, type=data_db_type["admin"])

        if int(super_admin["user_id"]) == user_id or result:
            msg = f"🚫@{user_name}已经是管理员了"
        else:
            result = db.insert(
                user_id=user_id, type=data_db_type["admin"], content=user_name
            )
            if result:
                msg = f"✅@{user_name}管理员设置成功！！"
            else:
                msg = f"🚫@{user_name}管理员设置失败, 请重试"

        status = bot.sendMessage(
            text=msg,
            chat_id=chat_id,
            parse_mode="HTML",
            reply_to_message_id=message_id,
        )
        bot.message_deletor(5, chat_id, status["message_id"])
