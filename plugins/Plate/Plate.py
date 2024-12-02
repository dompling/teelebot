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
import json, math, re


cookie_path = "Plate/115-cookie.txt"
available_app = "115android"

command = {  # 命令注册
    "/wpshare": "share",
    # "/wpupload": "upload",
    # "/wpdonwload": "download",
    "/wpoff": "off",
    "/wplogout": "logout",
}

command_text = {  # 命令注册
    "/wpshare": "网盘链接保存到",
    # "/wpupload": "上传到",
    # "/wpdonwload": "下载",
    "/wpoff": "离线任务保存到",
    "/wplogut": "登出当前账号",
}

# 每页显示的项目数量
ITEMS_PER_PAGE = 5


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


def get_folder(client: P115Client):
    fs = client.fs
    directory_list = fs.listdir_attr()
    return [item for item in directory_list if item.is_directory]


def build_menu(buttons, n_cols, header_buttons=None, footer_buttons=None):
    menu = [buttons[i : i + n_cols] for i in range(0, len(buttons), n_cols)]
    if header_buttons:
        menu.insert(0, header_buttons)
    if footer_buttons:
        menu.append(footer_buttons)
    return menu


def generate_pagination_keyboard(commands, directories, current_page, total_pages, cid):
    # 计算当前页面的开始和结束索引
    start = current_page * ITEMS_PER_PAGE
    end = min((current_page + 1) * ITEMS_PER_PAGE, len(directories))

    # 创建当前页面的按钮
    buttons = [
        {"text": d["name"], "callback_data": f"{commands} cd {d['id']}"}
        for i, d in enumerate(directories[start:end], start=start)
    ]

    footer_buttons = []
    # 创建分页按钮
    if current_page > 0:
        footer_buttons.append(
            {"text": "<<", "callback_data": f"{commands} page?page={current_page-1}"}
        )
    if current_page < total_pages - 1:
        footer_buttons.append(
            {"text": ">>", "callback_data": f"{commands} page?page={current_page+1}"}
        )

    header_buttons = [
        {
            "text": f"{command_text[commands]}当前目录",
            "callback_data": f"{commands} {cid}",
        }
    ]

    if cid != 0:
        header_buttons.insert(
            0, {"text": "上级目录", "callback_data": f"{commands} .."}
        )

    return build_menu(
        buttons,
        n_cols=3,
        header_buttons=header_buttons,
        footer_buttons=footer_buttons,
    )


def get_page_btn(commands, client: P115Client, current, cid):
    folder = get_folder(client)
    total_pages = math.ceil(len(folder) / ITEMS_PER_PAGE)
    inlineKeyboard = generate_pagination_keyboard(
        commands, folder, current, total_pages, cid
    )
    reply_markup = {"inline_keyboard": inlineKeyboard}
    return reply_markup


def Plate(bot, message):
    gap = 15
    message_id = message["message_id"]
    text = message.get("text", "")
    chat_id = message["chat"]["id"]
    message_type = message["message_type"]
    chat_type = message["chat"]["type"]
    bot_id = bot.bot_id
    root_id = bot.root_id
    user_id = message["from"]["id"]

    callback_query_data = message.get("callback_query_data", None)

    plugin_dir = bot.plugin_dir

    with open(bot.path_converter(plugin_dir + "Plate/icon.jpg"), "rb") as p:
        photo = p.read()

    prefix = ""
    ok, metadata = bot.metadata.read()
    if ok:
        prefix = metadata.get("Command", "")

    if message_type not in ["text", "callback_query_data"] or chat_type == "channel":
        return

    if message["chat"]["type"] != "private":
        admins = administrators(bot=bot, chat_id=chat_id)
        admins.append(bot_id)
        if str(root_id) not in admins:
            admins.append(str(root_id))  # root permission

    if message["chat"]["type"] != "private":
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

    if str(user_id) not in admins:
        msg = "权限不足，请授予全部权限以使用 Admin 插件。"
        status = bot.sendMessage(chat_id=chat_id, text=msg, parse_mode="HTML")
        bot.message_deletor(30, chat_id, status["message_id"])
        return

    count = 0
    for c in command.keys():
        if c in str(text):
            count += 1

    cookies = get_cookie(bot.path_converter(f"{bot.plugin_dir}{cookie_path}"))
    client = P115Client(cookies, app=available_app, check_for_relogin=True)

    # 检查登录
    if client.login_status() == False and message_type != "callback_query_data":
        status = sendLoginActions(
            bot,
            message,
            photo,
            [
                [
                    {"text": "115扫码登录", "callback_data": f"{prefix}-login"},
                ],
            ],
        )
        bot.message_deletor(8, chat_id, status["message_id"])
        return
    # /wp 插件功能
    elif text == prefix and count == 0:
        status = bot.sendChatAction(chat_id=chat_id, action="typing")
        msg = (
            "<b>115网盘 插件功能</b>\n\n"
            + "<b>/wpshare</b> - 引用分享链接保存到网盘\n"
            + "<b>/wpoff</b> - 引用磁力链保存到网盘\n"
            + "<b>/wplogout</b> - 引用磁力链保存到网盘\n"
            + "\n"
        )
        status = bot.sendMessage(
            chat_id=chat_id,
            text=msg,
            parse_mode="HTML",
            reply_to_message_id=message["message_id"],
        )
        bot.message_deletor(10, chat_id, status["message_id"])
        return
    elif text == prefix + command["/wplogout"]:
        client.logout()
        status = sendLoginActions(
            bot,
            message,
            photo,
            [
                [
                    {"text": "115扫码登录", "callback_data": f"{prefix}-login"},
                ],
            ],
        )
        bot.message_deletor(8, chat_id, status["message_id"])
        return
    # 命令插件功能
    elif message_type == "callback_query_data":
        reply_to_message = message.get("reply_to_message")
        callback_query_data = message["callback_query_data"]
        click_user_id = message["click_user"]["id"]

        if "reply_to_message" in message.keys():
            from_user_id = reply_to_message["from"]["id"]
        else:
            from_user_id = bot.bot_id
        if click_user_id == from_user_id:
            call = callback_query_data.split(" ")
            if "login" in callback_query_data:
                handle_login(bot, message, client)
            elif "page?page=" in callback_query_data:
                page = int(callback_query_data.split("=")[1])
                handle_sendMessage(bot, message, client, call, True, page)
            elif prefix + command[call[0]] == call[0]:
                handle_files_command(bot, message, client, call)
        else:
            status = bot.answerCallbackQuery(
                callback_query_id=message["callback_query_id"],
                text="点啥点，关你啥事？",
                show_alert=True,
            )

    elif "reply_to_message" in message.keys() and message_type != "callback_query_data":
        #  初次发送引用内容
        reply_to_message = message["reply_to_message"]
        target_chat_id = reply_to_message["chat"]["id"]
        if str(chat_id) == str(target_chat_id) and command.get(text):
            client.fs.chdir(0)
            handle_sendMessage(bot, message, client, [text, "cd", 0], False)
        return


"""
消息固定为: 
    当前目录：/ \n 引用内容xxx
    引用内容为操作的 115 链接，视频文件，磁力链等
"""


# 解析方式
def handle_sendMessage(
    bot, message, client: P115Client, actions=[], is_edit=True, page=0
):
    chat_id = message["chat"]["id"]
    message_id = message["message_id"]
    reply_to_message = message["reply_to_message"]

    current_path = client.fs.getcwd()
    status = bot.sendChatAction(chat_id=chat_id, action="typing")
    header = "<b>当前目录：" + current_path + "</b>"
    msg = []
    if is_edit == False:
        msg.append(header)
        msg.append(reply_to_message["text"])
        botAction = bot.sendMessage
    else:
        msg = message.get("text").split("\n")
        msg[0] = header
        botAction = bot.editMessageText
    msg = "\n".join(msg)
    status = botAction(
        chat_id=chat_id,
        text=msg,
        parse_mode="HTML",
        message_id=message_id,
        reply_to_message_id=message_id,
        reply_markup=get_page_btn(
            f"{actions[0]}",
            client=client,
            current=page,
            cid=actions[2],
        ),
    )
    bot.message_deletor(50, message["chat"]["id"], status["message_id"])


# 处理目录操作
def handle_files_command(bot, message, client: P115Client, actions=[]):
    text = message.get("text", "")
    if actions[1] == "cd":
        client.fs.chdir(int(actions[2]))
        handle_sendMessage(bot, message, client, actions)
    elif actions[1] == "..":
        texts = text.split("\n")
        current_path = texts[0].split("：")[1].split("/")
        pre_path = "/".join(current_path[0:-1])
        client.fs.chdir(pre_path)
        cid = client.fs.getcid()
        handle_sendMessage(bot, message, client, [actions[0], "cd", cid])
    else:
        handle_command(bot, message, client, actions)


"""
处理 command 列表中的命令
actions 固定为 [命令,cid]
"""


def handle_command(bot, message, client: P115Client, actions):
    message_id = message["message_id"]
    text = message.get("text", "")
    texts = text.split("\n")
    url = texts[1]
    bot.message_deletor(2, message["chat"]["id"], message_id)
    if command[actions[0]] == command["/wpshare"]:
        handle_save_share_url(bot, message, client, url, actions[1])
    elif command[actions[0]] == command["/wpoff"]:
        handle_magnet_url(bot, message, client, url, actions[1])


def handle_magnet_url(bot, message, client: P115Client, url, save_path):
    chat_id = message["chat"]["id"]
    message_id = message["message_id"]
    response = client.offline_add_url({"url": url, "wp_path_id": save_path})
    print(response)
    text = f"{url}离线任务保存成功"
    if response.get("error_msg"):
        text = response["error_msg"]
    status = bot.sendMessage(
        chat_id=chat_id,
        text=text,
        parse_mode="HTML",
        reply_to_message_id=message_id,
    )
    bot.message_deletor(5, message["chat"]["id"], status["message_id"])


# 保存分享链接
def handle_save_share_url(bot, message, client: P115Client, url, save_path):
    pattern = r"^https?:\/\/115\.com\/s\/(?P<share_code>[a-zA-Z0-9]+)\?password=(?P<receive_code>[a-zA-Z0-9]+)#?$"
    match = re.match(pattern, url)
    chat_id = message["chat"]["id"]
    message_id = message["message_id"]

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
        text = url + "分享保存成功"
        if response["error"]:
            text = response["error"]
        status = bot.sendMessage(
            chat_id=chat_id,
            text=text,
            parse_mode="HTML",
            reply_to_message_id=message_id,
        )
        bot.message_deletor(5, message["chat"]["id"], status["message_id"])

    else:
        status = bot.sendMessage(
            chat_id=chat_id,
            text="分享链接错误",
            parse_mode="HTML",
            reply_to_message_id=message_id,
        )
        bot.message_deletor(5, message["chat"]["id"], status["message_id"])
        return


# 登录
def handle_login(bot, message, client: P115Client):
    chat_id = message["chat"]["id"]
    message_id = message["message_id"]
    response = client.login_qrcode_token()
    qrcode_token = response["data"]
    url = client.login_qrcode(qrcode_token["uid"])
    status = bot.sendPhoto(chat_id=chat_id, photo=url, reply_to_message_id=message_id)

    while True:
        try:
            resp = client.login_qrcode_scan_status(qrcode_token)
        except Exception:
            continue
        match resp["data"].get("status"):
            case 0:
                print("[status=0] qrcode: waiting")
            case 1:
                print("[status=1] qrcode: scanned")
            case 2:
                print("[status=2] qrcode: signed in")
                resp = client.login_qrcode_scan_result(
                    uid=qrcode_token["uid"], app=available_app
                )
                break
            case -1:
                raise LoginError(errno.EIO, "[status=-1] qrcode: expired")
            case -2:
                raise LoginError(errno.EIO, "[status=-2] qrcode: canceled")
            case _:
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
    status = bot.sendChatAction(chat_id=chat_id, action="typing")
    msg = "🤖 115网盘登录成功\n📢请重新唤起机器人"
    status = bot.sendMessage(chat_id=chat_id, text=msg)
    bot.message_deletor(5, chat_id, status["message_id"])

    return resp


def sendLoginActions(bot, message, photo, inlineKeyboard):
    chat_id = message["chat"]["id"]
    message_id = message["message_id"]

    reply_markup = {"inline_keyboard": inlineKeyboard}
    status = bot.sendChatAction(chat_id=chat_id, action="typing")
    msg = ""

    status = bot.sendPhoto(
        chat_id=chat_id,
        photo=photo,
        caption=msg,
        parse_mode="HTML",
        reply_to_message_id=message_id,
        reply_markup=reply_markup,
    )

    return status


def administrators(bot, chat_id):
    admins = []
    results = bot.getChatAdministrators(chat_id=chat_id)
    if results != False:
        for result in results:
            if str(result["user"]["is_bot"]) == "False":
                admins.append(str(result["user"]["id"]))
    else:
        admins = False

    return admins
