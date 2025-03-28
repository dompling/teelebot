# -*- coding:utf-8 -*-
import os, json, time, re
from .quark_auto_save import Quarks, do_save, do_sign, do_save_subs
from .db import SqliteDB
from .config import Config


data_db_type = {
    "cookie": "cookie",
    "path": "path",
    "auto_save": "auto_save",
    "admin": "admin",
    "rec_pwd": "rec_pwd",
    "super_admin": "super_admin",
}

gaps = {
    "1s": 1,
    "2s": 2,
    "5s": 5,
    "10s": 10,
    "15s": 15,
    "30s": 30,
    "45s": 45,
    "1m": 60,
    "2m": 120,
    "5m": 300,
    "10m": 600,
    "15m": 900,
    "30m": 1800,
    "45m": 2700,
    "1h": 3600,
    "2h": 7200,
    "4h": 10800,
    "6h": 21600,
    "8h": 28800,
    "10h": 36000,
    "12h": 43200,
    "1d": 86400,
    "3d": 259200,
    "5d": 432000,
    "7d": 604800,
    "10d": 864000,
    "15d": 1296000,
    "20d": 1728000,
    "30d": 2592000,
}


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

auto_save_config = Config()


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

    save_path = db.find(user_id=user_id, type=data_db_type["path"])
    cookies = db.find(user_id=user_id, type=data_db_type["cookie"])

    savepath = False
    cookie = False

    if save_path:
        savepath = save_path["content"]
    if cookies:
        cookie = cookies["content"]

    account = Quarks(cookie, 0)
    if text[: len(prefix)] == prefix:
        if super_admin == False and text.startswith(f"{prefix}admin"):
            return handle_admin_commands(bot, message, db, super_admin)

        if check_user_admin(bot, message, super_admin, is_admin) == False:
            return

        bot.message_deletor(gap, message["chat"]["id"], message_id)

        if text == prefix:
            notify_body = [
                f"使用命令：",
                "<b>/qk</b> - 帮助",
                "<b>/qkset</b> - 设置 Cookie",
                "<b>/qkadmin</b> - 设置管理",
                "<b>/qkpath</b> - 设置账号",
                "<b>/qksign</b> - 签到",
                "<b>/qksub</b> - 更新订阅链接",
            ]
            notify_body = "\n".join(notify_body)
            notify_body += (
                "\n<b>/qksub</b> - 命令+周期，定期更新\n<b>支持的周期指令：</b> \n\n"
                + "<b>1s 2s 5s 10s 15s 30s 45s \n"
                + "1m 2m 5m 10m 15m 30m 45m \n"
                + "1h 2h 4h 6h 8h 10h 12h \n"
                + "1d 3d 5d 7d 10d 15d 20d 30d"
                + "</b>"
            )
            status = bot.sendMessage(
                text=notify_body,
                chat_id=chat_id,
                parse_mode="HTML",
                reply_to_message_id=message_id,
            )
            return bot.message_deletor(60, chat_id, status["message_id"])

        elif text[: len(prefix + "sub")] == prefix + "sub":
            notify_body = []
            try:
                notify_body, task_list = do_save_subs(account)

                if task_list:
                    for task in task_list:
                        task_config = auto_save_config.get_config(task)
                        if task_config:
                            account.do_rename_task(task_config)

            except Exception as e:
                notify_body = [f"❌❌订阅更新异常：{e}"]

            if message.get("action") == "cron":
                timestamp = time.strftime(
                    "%Y/%m/%d %H:%M:%S", time.localtime(time.time())
                )
                notify_body.insert(0, f"<b>时间：</b>{timestamp}\n")
                notify_body.insert(0, f"<b>⏰ 定时任务</b>\n")

            notify_body = "\n".join(notify_body)
            print(notify_body)
            bot.sendMessage(
                chat_id=chat_id,
                text=notify_body,
                parse_mode="HTML",
            )

            return

        elif text[: len(prefix + "sign")] == prefix + "sign":
            notify_body = do_sign(account)
            notify_body = "\n".join(notify_body)
            bot.sendMessage(
                chat_id=message["chat"]["id"],
                text=notify_body,
                parse_mode="HTML",
            )
            return

        elif text[: len(prefix + "set")] == prefix + "set":
            cookies = text.split(f"{prefix}set ")[1]
            db.insert_or_update(
                user_id=user_id, content=cookies, type=data_db_type["cookie"]
            )
            status = bot.sendMessage(
                text="✅ Cookies 保存成功",
                chat_id=chat_id,
                parse_mode="HTML",
                reply_to_message_id=message_id,
            )
            return bot.message_deletor(5, chat_id, status["message_id"])

        elif text[: len(prefix + "path")] == prefix + "path":
            path = text.split(f"{prefix}path ")[1]
            db.insert_or_update(
                user_id=user_id, content=path, type=data_db_type["path"]
            )
            status = bot.sendMessage(
                text=f"✅ 默认分享链接保存路径为{path}",
                chat_id=chat_id,
                parse_mode="HTML",
                reply_to_message_id=message_id,
            )
            return bot.message_deletor(5, chat_id, status["message_id"])
    elif (
        str(user_id) == bot_id
        or (message.get("reply_to_message") and chat_type != "private")
        or not is_admin
    ):
        return

    form_url = account.get_id_from_url(json.dumps(message, ensure_ascii=False))

    if form_url[3]:
        uri = form_url[3]
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

        task = {
            "taskname": "夸克机器人保存任务",
            "shareurl": uri,
            "savepath": savepath,
            "pattern": "",
            "replace": "",
            "enddate": "2099-01-30",
        }

        if message.get("text"):
            sub = message.get("text").split(" ")
            if len(sub) > 1 and sub[1]:
                task["taskname"] = sub[1]
                task["pattern"] = "^(\d+)(_|\s)?(【4K】|4K)?"
                task["replace"] = "$TASKNAME \\1"
                task["savepath"] = f"{savepath}/{sub[1]}"

            if len(sub) > 2:
                _, save_key = macth_content(task["shareurl"])
                auto_save_config.set_config(save_key, task)

        notify_body = do_save(account, [task])
        notify_body = "\n".join(notify_body)

        bot.sendMessage(
            chat_id=message["chat"]["id"],
            text=notify_body,
            parse_mode="HTML",
        )


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
