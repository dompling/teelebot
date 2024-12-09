# -*- coding:utf-8 -*-
from p115 import (
    P115Client,
    LoginError,
    check_response,
    AuthenticationError,
)
import sys, os
import errno
from builtins import setattr
import json, math, re, time, sqlite3
import teelebot
from collections import deque
from time import perf_counter
from yarl import URL


cookie_path = "Plate/115-cookie.txt"
available_app = "115android"

prefix = "/wp"

url_115_params = r"(?:https?:\/\/)?(?:www\.)?115\.com\/s\/(?P<share_code>[a-zA-Z0-9]+)(?:\?password=(?P<receive_code>[a-zA-Z0-9]+))?"
url_115_rex = r"(?:https?:\/\/)?(?:www\.)?115\.com\/s\/([a-zA-Z0-9]+)(?:\?password=([a-zA-Z0-9]+))?"

command = {  # 命令注册
    "/wpsave": "save",
    "/wpdel": "del",
    "/wpconfig": "config",
    "/wpcset": "cset",
    "/wpcdel": "cdel",
    "/wplogout": "logout",
    "/wplogin": "login",
    "/wprec": "rec",
    "/wprecp": "recp",
}

command_text = {  # 命令注册
    "/wpsave": "保存",
    "/wpdel": "删除",
    "/wpconfig": "115网盘设置",
    "/wpcset": "默认到",
    "/wpcdel": "删除默认",
    "/wplogut": "登出当前账号",
    "/wplogin": "115网盘登录",
}

# 每页显示的项目数量
ITEMS_PER_PAGE = 5

logo = "https://raw.githubusercontent.com/dompling/teelebot/refs/heads/plugin/plugins/Plate/icon.jpg"

log_dir = teelebot.bot.plugin_dir + "Plate/icon.jpg"

with open(teelebot.bot.path_converter(log_dir), "rb") as p:
    logo = p.read()


data_db_type = {
    "path": "path",
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
            bot.path_converter(plugin_dir + "Plate/data.db"), check_same_thread=False
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


def Plate(bot, message):
    gap = 15
    message_id = message["message_id"]
    text = message.get("text", "")
    chat_id = message["chat"]["id"]
    user_id = message["from"]["id"]
    message_type = message["message_type"]
    chat_type = message["chat"]["type"]
    bot_id = bot.bot_id

    if chat_type != "private":
        results = bot.getChatAdministrators(chat_id=chat_id)  # 判断Bot是否具管理员权限
        admin_status = False
        for admin_user in results:
            if str(admin_user["user"]["id"]) == str(bot_id):
                admin_status = True
        if admin_status != True:
            status = bot.sendChatAction(chat_id=chat_id, action="typing")
            msg = "权限不足，请授予全部权限以使用 Admin 插件。"
            status = bot.sendMessage(chat_id=chat_id, text=msg, parse_mode="HTML")
            bot.message_deletor(30, chat_id, status["message_id"])
            bot.message_deletor(gap, chat_id, message_id)
            return False

    if (
        text.startswith("/wp") == False
        and chat_type != "private"
        and message_type != "callback_query_data"
    ):
        return

    if str(user_id) == bot_id and message_type != "callback_query_data":
        return

    count = 0
    for c in command.keys():
        if c in str(text):
            count += 1

    plugin_dir = bot.plugin_dir
    db = SqliteDB(bot, plugin_dir)

    cookies = get_cookie(bot.path_converter(f"{bot.plugin_dir}{cookie_path}"))
    client = P115Client(cookies, app=available_app, check_for_relogin=True)

    super_admin = db.find_type(data_db_type["super_admin"])
    admin = db.find(user_id=user_id, type=data_db_type["admin"])

    is_admin = admin
    if is_admin == False and super_admin:
        is_admin = int(super_admin["user_id"]) == user_id

    if text[0:3] == prefix:
        bot.message_deletor(5, message["chat"]["id"], message_id)

    if message_type == "callback_query_data":
        callback_query_data = message["callback_query_data"]
        result = handle_callback_query(bot, message, callback_query_data)
        if result == False:
            return
        return handle_common_actions(bot, message, client, db)

    elif text.startswith("/wp"):
        if cookies:
            if super_admin == False and text.startswith("/wpadmin"):
                return handle_admin_commands(bot, message, db, super_admin)
            elif check_user_admin(bot, message, super_admin, is_admin) == False:
                return
            if text == "/wp":
                return send_plugin_info(bot, chat_id, message_id)
            elif text.startswith("/wpconfig"):
                return handle_wpconfig(bot, message, client, db)
            elif text.startswith("/wprecp"):
                return handle_set_recycle_pwd(bot, message, db, user_id)
            elif text.startswith("/wplogout"):
                return handle_logout(bot, message, client)
            elif text.startswith("/wpadmin"):
                return handle_admin_commands(bot, message, db, super_admin)
            elif text.startswith("/wpsave"):
                return handle_wp_save(bot, message, client, db)
        else:
            handle_login(bot, message)

    elif chat_type == "private":
        """处理私聊，直接保存功能"""
        if cookies and count == 0:
            reply_to_message = message.get("reply_to_message", message)
            content = reply_to_message.get("text", reply_to_message.get("caption", ""))
            share_type = macth_content(content)
            if share_type:
                handle_wp_save(bot, message, client, db)


def handle_save_file(bot, message, client: P115Client, db: SqliteDB):
    user_id = message["from"]["id"]
    user_default_path = db.find(user_id=user_id, type=data_db_type["path"])
    if user_default_path == False:
        return

    file_id = ""
    file_size = -1
    file_name = ""
    if message.get("photo"):
        photo = max(message["photo"], key=lambda x: x["file_size"])
        file_id = photo["file_id"]
        file_size = photo["file_size"]
        file_name = photo["file_unique_id"] + ".png"
    elif message.get("video"):
        file_id = message["video"]["file_id"]
        file_size = message["video"]["file_size"]
        file_name = message["video"]["file_name"]

    if file_id:
        file_dl_path = bot.getFileDownloadPath(file_id=file_id)
        chat_id = message["chat"]["id"]

        file_content = URL(file_dl_path)

        status = bot.sendPhoto(
            chat_id=chat_id,
            caption="💾上传中...",
            photo=logo,
            parse_mode="HTML",
            reply_to_message_id=message["message_id"],
        )

        def make_reporthook(total: None | int = None):
            return make_report(bot, status, total)

        resp = client.upload_file(
            file=file_content,
            pid=int(user_default_path["content"]),
            filename=file_name,
            close_file=True,
            make_reporthook=make_reporthook,
        )
        msg = f"✅上传成功"
        if resp.get("statusmsg"):
            msg = resp["statusmsg"]
        update_msg_text(bot, status, msg)


def handle_wp_save(bot, message, client: P115Client, db: SqliteDB):
    user_id = message["from"]["id"]
    user_default_path = db.find(user_id=user_id, type=data_db_type["path"])
    if user_default_path == False:
        handle_sendMessage(
            bot=bot,
            message=message,
            client=client,
            actions=["/wpsave", "c", 0, message["from"]["id"]],
            is_edit=False,
        )
    else:
        actions = ["/wpsave", "e", user_default_path["content"], user_id]
        handle_common_actions(bot, message, client, db, actions)


def handle_save_action(bot, message, client: P115Client, action: str, db: SqliteDB):
    reply_to_message = message.get("reply_to_message", message)
    content = reply_to_message.get("text", reply_to_message.get("caption", ""))
    share_type, url = macth_content(content)
    if share_type == "115_url":
        handle_save_share_url(bot, message, client, url, action)
    elif share_type == "magent_url":
        handle_magnet_url(bot, message, client, url, action)
    elif "video" in reply_to_message.keys() or "photo" in reply_to_message.keys():
        handle_save_file(bot, reply_to_message, client, db)


def handle_callback_query(bot, message, callback_query_data: str):
    # 解析回调数据
    actions = callback_query_data.split("|")
    click_user_id = message["click_user"]["id"]  # 点击者的用户 ID
    if not command.get(actions[0]):
        bot.answerCallbackQuery(
            callback_query_id=message["callback_query_id"],
            text=f"🚫 未注册命令{actions[0]}？",
            show_alert=True,
        )
        return False
    # 检查是否是同一个用户
    if str(click_user_id) not in actions:
        # 如果不是同一个用户，拒绝操作
        bot.answerCallbackQuery(
            callback_query_id=message["callback_query_id"],
            text="🚫 点啥点，关你啥事？",
            show_alert=True,
        )
        return False
    return True


def check_user_admin(bot, message, super_admin: bool, is_admin: bool):
    """
    是否是Bot管理员验证登录
    """
    chat_type = message["chat"]["type"]
    message_id = message["message_id"]
    chat_id = message["chat"]["id"]
    msg = ""
    if super_admin == False and chat_type != "private":
        msg = "🚫当前机器人暂无管理员\n请私聊执行<b>/wpadmin</b>"
    elif super_admin == False and chat_type == "private":
        msg = "🚫当前机器人暂无管理员\n请执行<b>/wpadmin</b>"
    elif is_admin == False:
        msg = "🚫您当前暂无机器人管理权限\n请私聊管理员获取"
    if msg:
        status = bot.sendPhoto(
            caption=msg,
            photo=logo,
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
                "✅超级管理员初始化成功\n可引用消息，执行<b>/wpadmin</b>设置其他管理员"
            )
        else:
            msg = "🚫超级管理员初始化失败, 请重试"
        status = bot.sendPhoto(
            caption=msg,
            photo=logo,
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
        status = bot.sendPhoto(
            caption=msg,
            photo=logo,
            chat_id=chat_id,
            parse_mode="HTML",
            reply_to_message_id=message_id,
        )
        bot.message_deletor(5, chat_id, status["message_id"])


def handle_login(bot, message):
    """登录"""
    chat_id = message["chat"]["id"]
    message_id = message["message_id"]
    user_id = message["from"]["id"]
    reply_markup = {
        "inline_keyboard": [
            [{"text": "115扫码登录", "callback_data": f"/wplogin|{user_id}"}]
        ]
    }
    status = bot.sendChatAction(chat_id=chat_id, action="typing")
    status = bot.sendPhoto(
        chat_id=chat_id,
        photo=logo,
        reply_to_message_id=message_id,
        reply_markup=reply_markup,
    )
    bot.message_deletor(8, chat_id, status["message_id"])


def send_plugin_info(bot, chat_id, message_id):
    """发送插件功能信息"""
    msg = (
        "<b>115网盘 插件功能</b>\n\n"
        + "<b>/wpsave</b> - 内容保存到网盘\n"
        + "<b>/wplogout</b> - 退出重新登录\n"
        + "<b>/wpadmin</b> - 设置管理员\n"
        + "<b>/wpconfig</b> - 网盘配置\n"
        + "<b>/wprecp</b> - 回收站密码（命令+空格+密码）"
    )
    status = bot.sendMessage(
        chat_id=chat_id,
        text=msg,
        parse_mode="HTML",
        reply_to_message_id=message_id,
    )
    bot.message_deletor(10, chat_id, status["message_id"])


def handle_wpconfig(bot, message, client: P115Client, db: SqliteDB):
    message_id = message.get("message_id", "")
    chat_id = message["chat"]["id"]
    user_name = message["from"]["username"]  # 点击者的用户 ID
    user_id = message["from"]["id"]  # 点击者的用户 ID
    result = db.find(user_id=user_id, type=data_db_type["path"])

    msg = f"<b>🖥️当前管理:{user_name}</b>"
    if result:
        cid = result["content"]
        client.fs.chdir(int(cid))
        current_path = client.fs.getcwd()
        if current_path == "/":
            current_path = "根目录"
        msg += f"\n<b>🗂️默认保存：{current_path}</b>"

    fs_info = client.fs_index_info()
    if fs_info["error"] == "":
        wp_info = fs_info["data"]
        device_list = wp_info["login_devices_info"]["list"]
        use_info = (
            wp_info["space_info"]["all_use"]["size_format"]
            + "/"
            + wp_info["space_info"]["all_total"]["size_format"]
        )
        device_names = ", ".join([device["name"] for device in device_list])
        msg += f"\n<b>⏲️网盘容量：{use_info}</b>"
        msg += f"\n<b>📟已登设备：{device_names}</b>"
    status = bot.sendChatAction(chat_id=chat_id, action="typing")
    status = bot.sendPhoto(
        chat_id=chat_id,
        caption=msg,
        photo=logo,
        parse_mode="HTML",
        reply_to_message_id=message_id,
        reply_markup={
            "inline_keyboard": [
                [
                    {"text": "设置默认目录", "callback_data": f"/wpcset|{user_id}"},
                    {"text": "删除默认目录", "callback_data": f"/wpcdel|{user_id}"},
                ],
                [
                    {"text": "删除文件或目录", "callback_data": f"/wpdel|{user_id}"},
                    {"text": "清空回收站", "callback_data": f"/wprec|{user_id}"},
                ],
                [
                    {"text": "取消", "callback_data": f"/wpconfig|d|0|{user_id}"},
                ],
            ]
        },
    )
    bot.message_deletor(90, message["chat"]["id"], status["message_id"])


def handle_common_actions(
    bot, message, client: P115Client, db: SqliteDB, default_actions=False
):
    """通用actions处理"""
    if default_actions:
        actions = default_actions
    else:
        callback_query_data = message.get("callback_query_data")
        actions = callback_query_data.split("|")
    # 0：commond 命令，1：目录操作命令(p翻译,d取消,c进入,.返回,e执行)，2：目录 id,3:用户 id
    click_user_id = message["click_user"]["id"]  # 点击者的用户 ID
    if len(actions) != 4:
        actions = [actions[0], "e", 0, actions[1]]
        if actions[0] == "/wpcset":
            handle_sendMessage(bot, message, client, actions)
            
        elif actions[0] == "/wpcdel":
            db.delete(click_user_id, data_db_type["path"])
            update_msg_text(bot, message, "✅删除网盘默认目录成功")
            
        elif actions[0] == "/wplogin":
            handle_qrcode_login(bot=bot, message=message, client=client)
            
        elif actions[0] == "/wprec":
            handle_clear_recycle(bot, message, client, db)
            
        elif actions[0] == "/wpdel":
            result = db.find(user_id=click_user_id, type=data_db_type["path"])
            if result:
                client.fs.chdir(int(result["content"]))
            handle_sendMessage(bot, message, client, actions, True, 0, True)
    else:
        if "p=" in actions[1]:
            """目录翻页"""
            page = int(actions[1].split("=")[1])
            client.fs.chdir(int(actions[2]))
            handle_sendMessage(bot, message, client, actions, True, page)

        if actions[1] == "d":
            """取消目录消息"""
            bot.message_deletor(1, message["chat"]["id"], message["message_id"])

        elif actions[1] == "c":
            """进入目录消息"""
            client.fs.chdir(int(actions[2]))
            handle_sendMessage(bot, message, client, actions)

        elif actions[1] == ".":
            """返回上级目录"""
            current_path = client.fs.get_path(actions[2])
            current_path = current_path.split("/")
            pre_path = "/".join(current_path[0:-1])
            client.fs.chdir(pre_path)
            cid = client.fs.getcid()
            actions[2] = cid
            handle_sendMessage(bot, message, client, actions)

        elif actions[1] == "e":
            """执行当前目录功能"""
            if command[actions[0]] == command["/wpsave"]:
                handle_save_action(bot, message, client, actions[2], db)

            elif command[actions[0]] == command["/wpcset"]:
                handle_set_default_path(bot, message, db, actions[2])

            elif command[actions[0]] == command["/wpdel"]:
                handle_del(bot, message, client, db, actions)


def handle_del(bot, message, client: P115Client, db, actions):
    msg = "✅删除成功"
    resp = client.fs_delete({"fid": [actions[2]]})
    if resp.get("error"):
        msg = f"🚫{resp.get('error')}"
    update_msg_text(bot, message, msg, {"inline_keyboard": []}, False)
    handle_common_actions(bot, message, client, db, [actions[0], "c", 0, actions[3]])


def handle_clear_recycle(bot, message, client: P115Client, db: SqliteDB):
    result = db.find_type(data_db_type["rec_pwd"])
    if result == False:
        msg = "🚫暂未设置清空回收站密码"
        return update_msg_text(bot, message, msg)
    rec_pwd = result["content"]
    response = client.recyclebin_clean({"password": rec_pwd})
    msg = "✅清空回收站成功"
    if response["error"]:
        msg = response["error"]
    return update_msg_text(bot, message, msg)


def handle_set_recycle_pwd(bot, message, db: SqliteDB, user_id):
    try:
        result = db.find_type(data_db_type["rec_pwd"])
        cmd, pwd = message.get("text", "").split(" ")
        if result == False:
            db.insert(user_id, pwd, data_db_type["rec_pwd"])
        else:
            db.update_type(data_db_type["rec_pwd"], pwd)
        msg = "✅回收站密码设置成功"
        return update_msg_text(bot, message, msg)
    except ValueError:
        return update_msg_text(bot, message, "🚫密码设置失败，请检查")


def handle_set_default_path(bot, message, db: SqliteDB, action):
    click_user_id = message["click_user"]["id"]  # 点击者的用户 ID
    result = db.find(user_id=click_user_id, type=data_db_type["path"])
    if result == False:
        db.insert(
            user_id=click_user_id,
            content=action,
            type=data_db_type["path"],
        )
    else:
        db.update(
            user_id=click_user_id,
            content=action,
            type=data_db_type["path"],
        )
    update_msg_text(bot, message, "✅设置网盘默认目录成功")


def handle_logout(bot, message, client: P115Client):
    """处理退出登录"""
    client.logout()
    handle_login(bot=bot, message=message)


# 解析方式
def handle_sendMessage(
    bot, message, client: P115Client, actions=[], is_edit=True, page=0, has_file=False
):
    """
    消息固定为:
        当前目录：/ \n 引用内容xxx
        引用内容为操作的 115 链接，视频文件，磁力链等
    """

    chat_id = message["chat"]["id"]
    message_id = message["message_id"]
    reply_to_message = message.get("reply_to_message", message)

    current_path = client.fs.getcwd()
    status = bot.sendChatAction(chat_id=chat_id, action="typing")
    msg = "当前目录：" + current_path
    if is_edit == False:
        message_id = reply_to_message.get("message_id")
        status = bot.sendPhoto(
            chat_id=chat_id,
            caption=msg,
            photo=logo,
            parse_mode="HTML",
            reply_to_message_id=message_id,
            reply_markup=get_page_btn(
                actions,
                client=client,
                current=page,
                has_file=has_file,
            ),
        )
    else:
        status = bot.editMessageCaption(
            chat_id=chat_id,
            caption=msg,
            message_id=message_id,
            reply_markup=get_page_btn(
                actions,
                client=client,
                current=page,
                has_file=has_file,
            ),
        )
    if status and status["message_id"]:
        bot.message_deletor(90, message["chat"]["id"], status["message_id"])
    else:
        time.sleep(1)  # 睡眠1秒
        handle_sendMessage(bot, message, client, actions, is_edit, page)


def handle_magnet_url(bot, message, client: P115Client, url, save_path):
    response = client.offline_add_url({"url": url, "wp_path_id": save_path})
    text = message.get("caption", "") + "\n离线任务保存成功"
    if response.get("error_msg"):
        text = "🚫" + response["error_msg"]
    update_msg_text(bot, message, text)


# 保存分享链接
def handle_save_share_url(bot, message, client: P115Client, url, save_path):
    match = re.match(url_115_params, url)

    if match:
        share_code = match.group("share_code")
        receive_code = match.group("receive_code")
        share_params = {
            "share_code": share_code,
            "receive_code": receive_code,
        }
        share_files = client.share_snap(share_params)
        share_params["cid"] = save_path
        list_data = share_files["data"]["list"]
        share_params["file_id"] = ",".join(
            [item.get("fid", item.get("cid")) for item in list_data]
        )
        response = client.share_receive(share_params)
        text = message.get("caption", "") + "\n分享任务保存成功"
        if response["error"]:
            text = "🚫" + response["error"]
        update_msg_text(bot, message, text)

    else:
        update_msg_text(bot, message, "🚫分享链接错误")


# 登录
def handle_qrcode_login(bot, message, client: P115Client):
    chat_id = message["chat"]["id"]
    message_id = message["message_id"]
    response = client.login_qrcode_token()
    qrcode_token = response["data"]
    url = client.login_qrcode(qrcode_token["uid"])
    reply_markup = {
        "inline_keyboard": [[{"text": "刷新二维码", "callback_data": "/wplogin"}]]
    }

    bot.message_deletor(1, chat_id, message_id)
    status = bot.sendPhoto(
        photo=url,
        chat_id=chat_id,
        caption="等待扫码中...",
    )

    message_id = status["message_id"]

    status = bot.sendChatAction(chat_id=chat_id, action="typing")

    while True:
        try:
            resp = client.login_qrcode_scan_status(qrcode_token)
        except Exception:
            continue
        match resp["data"].get("status"):
            case 0:
                print("[status=0] qrcode: waiting")
                status = bot.editMessageCaption(
                    chat_id=chat_id,
                    message_id=message_id,
                    caption="✅等待扫码中...",
                )
            case 1:
                print("[status=1] qrcode: scanned")
                status = bot.editMessageCaption(
                    chat_id=chat_id, message_id=message_id, caption="✅扫码确认中..."
                )
            case 2:
                status = bot.editMessageCaption(
                    chat_id=chat_id, message_id=message_id, caption="✅登录成功！！"
                )
                print("[status=2] qrcode: signed in")
                resp = client.login_qrcode_scan_result(
                    uid=qrcode_token["uid"], app=available_app
                )
                break
            case -1:
                update_msg_text(bot, message, "🚫二维码已过期", reply_markup)
                raise LoginError(errno.EIO, "[status=-1] qrcode: expired")
            case -2:
                update_msg_text(bot, message, "🚫扫码已取消", reply_markup)
                raise LoginError(errno.EIO, "[status=-2] qrcode: canceled")
            case _:
                update_msg_text(bot, message, "🚫扫码拒绝", reply_markup)
                raise LoginError(errno.EIO, f"qrcode: aborted with {resp!r}")
    bot.message_deletor(2, chat_id, status["message_id"])
    try:
        check_response(resp)
    except AuthenticationError:

        raise LoginError(errno.EIO, "[cookies=-1] cookie: is error")
    setattr(client, "cookies", resp["data"]["cookie"])

    save_cookie(
        bot.path_converter(f"{bot.plugin_dir}{cookie_path}"),
        json.dumps(resp["data"]["cookie"]),
    )
    return resp


def update_msg_text(
    bot, message, text, reply_markup={"inline_keyboard": []}, del_msg=True
):
    chat_id = message["chat"]["id"]
    message_id = message["message_id"]
    status = bot.editMessageCaption(
        chat_id=chat_id,
        caption=text,
        message_id=message_id,
        reply_markup=reply_markup,
    )
    if status == False:
        status = bot.sendPhoto(
            chat_id=chat_id,
            caption=text,
            photo=logo,
            parse_mode="HTML",
            reply_to_message_id=message_id,
        )
    if not del_msg:
        return status
    bot.message_deletor(5, message["chat"]["id"], status["message_id"])


def get_cookie(path):
    cookies = ""
    if os.path.exists(path):
        try:
            cookies = open(path).read()
            cookies = json.loads(cookies)
        except FileNotFoundError as e:
            print(f"Error: {e}")
            sys.exit(1)
    return cookies


def save_cookie(path, cookies):
    with open(path, "w", encoding="utf-8") as file:
        # 将内容写入文件
        file.write(cookies)


def get_folder(client: P115Client, has_file: bool = False):
    fs = client.fs
    directory_list = fs.listdir_attr()
    if has_file:
        return directory_list
    return [item for item in directory_list if item.is_directory]


def build_menu(buttons, n_cols, header_buttons=None, footer_buttons=None):
    menu = [buttons[i : i + n_cols] for i in range(0, len(buttons), n_cols)]
    if header_buttons:
        menu.insert(0, header_buttons)
    if footer_buttons:
        menu.append(footer_buttons)
    return menu


def generate_pagination_keyboard(actions, directories, current_page, total_pages):
    # 计算当前页面的开始和结束索引
    start = current_page * ITEMS_PER_PAGE
    end = min((current_page + 1) * ITEMS_PER_PAGE, len(directories))

    c = actions[0]
    cid = actions[2]
    userid = actions[3]
    # 创建当前页面的按钮
    buttons = [
        {
            "text": f"🗂️{d['name']}" if d["is_dir"] else f"📒{d['name']}",
            "callback_data": f"{c}|{('c' if d['is_dir'] else 'e')}|{d['id']}|{userid}",
        }
        for i, d in enumerate(directories[start:end], start=start)
    ]

    footer_buttons = []
    # 创建分页按钮
    if current_page > 0:
        footer_buttons.append(
            {
                "text": "上一页",
                "callback_data": f"{c}|p={current_page-1}|{cid}|{userid}",
            }
        )
    if current_page < total_pages - 1:
        footer_buttons.append(
            {
                "text": "下一页",
                "callback_data": f"{c}|p={current_page+1}|{cid}|{userid}",
            }
        )

    header_buttons = [
        {
            "text": "🗑️取消",
            "callback_data": f"{c}|d|{cid}|{userid}",
        },
        {
            "text": f"❤️{command_text[c]}",
            "callback_data": f"{c}|e|{cid}|{userid}",
        },
    ]

    if int(cid) != 0:
        header_buttons.insert(
            1, {"text": "🔙返回", "callback_data": f"{c}|.|{cid}|{userid}"}
        )

    return build_menu(
        buttons,
        n_cols=3,
        header_buttons=header_buttons,
        footer_buttons=footer_buttons,
    )


def get_page_btn(actions, client: P115Client, current, has_file=False):
    folder = get_folder(client, has_file)
    total_pages = math.ceil(len(folder) / ITEMS_PER_PAGE)
    inlineKeyboard = generate_pagination_keyboard(actions, folder, current, total_pages)
    reply_markup = {"inline_keyboard": inlineKeyboard}
    return reply_markup


# 解析链接
def macth_content(content):
    link = re.search(url_115_rex, content)
    if link:
        return "115_url", link.group(0)

    magnet_link = re.search(r"magnet:\?xt=urn:btih:[0-9a-fA-F]{40,}.*", content)
    if magnet_link:
        return "magent_url", magnet_link.group(0)

    ed2k_link = re.search(r"(ed2k://\|file\|.*?\|/\n)", content)
    if ed2k_link:
        return "magent_url", ed2k_link.group(1)

    return False, content


def make_report(bot, message, total: None | int = None):
    dq: deque[tuple[int, float]] = deque(maxlen=64)
    push = dq.append
    read_num = 0
    push((read_num, perf_counter()))
    while True:
        read_num += yield
        cur_t = perf_counter()
        speed = (read_num - dq[0][0]) / 1024 / 1024 / (cur_t - dq[0][1])
        if total:
            percentage = read_num / total * 100
            up_num = read_num / (1024 * 1024)
            total_num = total / (1024 * 1024)
            msg = f"\r\x1b[K{up_num:.2f}MB / {total_num:.2f}MB | {speed:.2f} MB/s | {percentage:.2f} %"
            print(msg, end="", flush=True)
            time.sleep(1)
            msg = f"{up_num:.2f}MB / {total_num:.2f}MB | {speed:.2f} MB/s | {percentage:.2f} %"
            bot.editMessageCaption(
                chat_id=message["chat"]["id"],
                caption=msg,
                message_id=message["message_id"],
            )
        else:
            msg = f"\r\x1b[K{(read_num / (1024 * 1024)):.2f}MB | {speed:.2f} MB/s"
            print(msg, end="", flush=True)
            time.sleep(1)
            msg = f"{(read_num / (1024 * 1024)):.2f}MB | {speed:.2f} MB/s"
            bot.editMessageCaption(
                chat_id=message["chat"]["id"],
                caption=msg,
                message_id=message["message_id"],
            )
        push((read_num, cur_t))
