# !/usr/bin/env python3
# -*- coding: utf-8 -*-
# Modify: 2024-11-13
# Repo: https://github.com/Cp0204/quark_auto_save
# ConfigFile: quark_config.json
"""
new Env('夸克自动追更');
0 8,18,20 * * * quark_auto_save.py
"""
import os
import re
import time
import random
import requests
from datetime import datetime
from treelib import Tree


CONFIG_DATA = {}
NOTIFYS = []
GH_PROXY = os.environ.get("GH_PROXY", "https://ghproxy.net/")


MAGIC_REGEX = {
    "$TV": {
        "pattern": r".*?(?<!\d)([Ss]\d{1,2})?([Ee]?[Pp]?[Xx]?\d{1,3})(?!\d).*?\.(mp4|mkv)",
        "replace": r"\1\2.\3",
    },
}


# 添加消息
def add_notify(text):
    global NOTIFYS
    NOTIFYS.append(text)
    print("📢", text)
    return text


class Quarks:
    BASE_URL = "https://drive-pc.quark.cn"
    BASE_URL_APP = "https://drive-m.quark.cn"
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) quark-cloud-drive/3.14.2 Chrome/112.0.5615.165 Electron/24.1.3.8 Safari/537.36 Channel/pckk_other_ch"

    def __init__(self, cookie, index=None):
        self.cookie = cookie.strip()
        self.index = index + 1
        self.is_active = False
        self.nickname = ""
        self.mparam = self._match_mparam_form_cookie(cookie)
        self.savepath_fid = {"/": "0"}

    def _match_mparam_form_cookie(self, cookie):
        mparam = {}
        kps_match = re.search(r"(?<!\w)kps=([a-zA-Z0-9%+/=]+)[;&]?", cookie)
        sign_match = re.search(r"(?<!\w)sign=([a-zA-Z0-9%+/=]+)[;&]?", cookie)
        vcode_match = re.search(r"(?<!\w)vcode=([a-zA-Z0-9%+/=]+)[;&]?", cookie)
        if kps_match and sign_match and vcode_match:
            mparam = {
                "kps": kps_match.group(1).replace("%25", "%"),
                "sign": sign_match.group(1).replace("%25", "%"),
                "vcode": vcode_match.group(1).replace("%25", "%"),
            }
        return mparam

    def _send_request(self, method, url, **kwargs):
        headers = {
            "cookie": self.cookie,
            "content-type": "application/json",
            "user-agent": self.USER_AGENT,
        }
        if "headers" in kwargs:
            headers = kwargs["headers"]
            del kwargs["headers"]
        if self.mparam and "share" in url and self.BASE_URL in url:
            url = url.replace(self.BASE_URL, self.BASE_URL_APP)
            kwargs["params"].update(
                {
                    "device_model": "M2011K2C",
                    "entry": "default_clouddrive",
                    "_t_group": "0%3A_s_vp%3A1",
                    "dmn": "Mi%2B11",
                    "fr": "android",
                    "pf": "3300",
                    "bi": "35937",
                    "ve": "7.4.5.680",
                    "ss": "411x875",
                    "mi": "M2011K2C",
                    "nt": "5",
                    "nw": "0",
                    "kt": "4",
                    "pr": "ucpro",
                    "sv": "release",
                    "dt": "phone",
                    "data_from": "ucapi",
                    "kps": self.mparam.get("kps"),
                    "sign": self.mparam.get("sign"),
                    "vcode": self.mparam.get("vcode"),
                    "app": "clouddrive",
                    "kkkk": "1",
                }
            )
            del headers["cookie"]
        try:
            response = requests.request(method, url, headers=headers, **kwargs)
            # print(f"{response.text}")
            # response.raise_for_status()  # 检查请求是否成功，但返回非200也会抛出异常
            return response
        except Exception as e:
            print(f"_send_request error:\n{e}")
            fake_response = requests.Response()
            fake_response.status_code = 500
            fake_response._content = b'{"status": 500, "message": "request error"}'
            return fake_response

    def init(self):
        account_info = self.get_account_info()
        if account_info:
            self.is_active = True
            self.nickname = account_info["nickname"]
            return account_info
        else:
            return False

    def get_account_info(self):
        url = "https://pan.quark.cn/account/info"
        querystring = {"fr": "pc", "platform": "pc"}
        response = self._send_request("GET", url, params=querystring).json()
        if response.get("data"):
            return response["data"]
        else:
            return False

    def get_growth_info(self):
        url = f"{self.BASE_URL_APP}/1/clouddrive/capacity/growth/info"
        querystring = {
            "pr": "ucpro",
            "fr": "android",
            "kps": self.mparam.get("kps"),
            "sign": self.mparam.get("sign"),
            "vcode": self.mparam.get("vcode"),
        }
        headers = {
            "content-type": "application/json",
        }
        response = self._send_request(
            "GET", url, headers=headers, params=querystring
        ).json()
        if response.get("data"):
            return response["data"]
        else:
            return False

    def get_growth_sign(self):
        url = f"{self.BASE_URL_APP}/1/clouddrive/capacity/growth/sign"
        querystring = {
            "pr": "ucpro",
            "fr": "android",
            "kps": self.mparam.get("kps"),
            "sign": self.mparam.get("sign"),
            "vcode": self.mparam.get("vcode"),
        }
        payload = {
            "sign_cyclic": True,
        }
        headers = {
            "content-type": "application/json",
        }
        response = self._send_request(
            "POST", url, json=payload, headers=headers, params=querystring
        ).json()
        if response.get("data"):
            return True, response["data"]["sign_daily_reward"]
        else:
            return False, response["message"]

    # 可验证资源是否失效
    def get_stoken(self, pwd_id, passcode=""):
        url = f"{self.BASE_URL}/1/clouddrive/share/sharepage/token"
        querystring = {"pr": "ucpro", "fr": "pc"}
        payload = {"pwd_id": pwd_id, "passcode": passcode}
        response = self._send_request(
            "POST", url, json=payload, params=querystring
        ).json()
        if response.get("status") == 200:
            return True, response["data"]["stoken"]
        else:
            return False, response["message"]

    def get_detail(self, pwd_id, stoken, pdir_fid, _fetch_share=0):
        list_merge = []
        page = 1
        while True:
            url = f"{self.BASE_URL}/1/clouddrive/share/sharepage/detail"
            querystring = {
                "pr": "ucpro",
                "fr": "pc",
                "pwd_id": pwd_id,
                "stoken": stoken,
                "pdir_fid": pdir_fid,
                "force": "0",
                "_page": page,
                "_size": "50",
                "_fetch_banner": "0",
                "_fetch_share": _fetch_share,
                "_fetch_total": "1",
                "_sort": "file_type:asc,updated_at:desc",
            }
            response = self._send_request("GET", url, params=querystring).json()
            if response["data"]["list"]:
                list_merge += response["data"]["list"]
                page += 1
            else:
                break
            if len(list_merge) >= response["metadata"]["_total"]:
                break
        response["data"]["list"] = list_merge
        return response["data"]

    def get_fids(self, file_paths):
        fids = []
        while True:
            url = f"{self.BASE_URL}/1/clouddrive/file/info/path_list"
            querystring = {"pr": "ucpro", "fr": "pc"}
            payload = {"file_path": file_paths[:50], "namespace": "0"}
            response = self._send_request(
                "POST", url, json=payload, params=querystring
            ).json()
            if response["code"] == 0:
                fids += response["data"]
                file_paths = file_paths[50:]
            else:
                print(f"获取目录ID：失败, {response['message']}")
                break
            if len(file_paths) == 0:
                break
        return fids

    def ls_dir(self, pdir_fid, **kwargs):
        file_list = []
        page = 1
        while True:
            url = f"{self.BASE_URL}/1/clouddrive/file/sort"
            querystring = {
                "pr": "ucpro",
                "fr": "pc",
                "uc_param_str": "",
                "pdir_fid": pdir_fid,
                "_page": page,
                "_size": "50",
                "_fetch_total": "1",
                "_fetch_sub_dirs": "0",
                "_sort": "file_type:asc,updated_at:desc",
                "_fetch_full_path": kwargs.get("fetch_full_path", 0),
            }
            response = self._send_request("GET", url, params=querystring).json()
            if response["data"]["list"]:
                file_list += response["data"]["list"]
                page += 1
            else:
                break
            if len(file_list) >= response["metadata"]["_total"]:
                break
        return file_list

    def save_file(self, fid_list, fid_token_list, to_pdir_fid, pwd_id, stoken):
        url = f"{self.BASE_URL}/1/clouddrive/share/sharepage/save"
        querystring = {
            "pr": "ucpro",
            "fr": "pc",
            "uc_param_str": "",
            "app": "clouddrive",
            "__dt": int(random.uniform(1, 5) * 60 * 1000),
            "__t": datetime.now().timestamp(),
        }
        payload = {
            "fid_list": fid_list,
            "fid_token_list": fid_token_list,
            "to_pdir_fid": to_pdir_fid,
            "pwd_id": pwd_id,
            "stoken": stoken,
            "pdir_fid": "0",
            "scene": "link",
        }
        response = self._send_request(
            "POST", url, json=payload, params=querystring
        ).json()
        return response

    def query_task(self, task_id):
        retry_index = 0
        while True:
            url = f"{self.BASE_URL}/1/clouddrive/task"
            querystring = {
                "pr": "ucpro",
                "fr": "pc",
                "uc_param_str": "",
                "task_id": task_id,
                "retry_index": retry_index,
                "__dt": int(random.uniform(1, 5) * 60 * 1000),
                "__t": datetime.now().timestamp(),
            }
            response = self._send_request("GET", url, params=querystring).json()
            if response["data"]["status"] != 0:
                if retry_index > 0:
                    print()
                break
            else:
                if retry_index == 0:
                    print(
                        f"正在等待[{response['data']['task_title']}]执行结果",
                        end="",
                        flush=True,
                    )
                else:
                    print(".", end="", flush=True)
                retry_index += 1
                time.sleep(0.500)
        return response

    def download(self, fids):
        url = f"{self.BASE_URL}/1/clouddrive/file/download"
        querystring = {"pr": "ucpro", "fr": "pc", "uc_param_str": ""}
        payload = {"fids": fids}
        response = self._send_request("POST", url, json=payload, params=querystring)
        set_cookie = response.cookies.get_dict()
        cookie_str = "; ".join([f"{key}={value}" for key, value in set_cookie.items()])
        return response.json(), cookie_str

    def mkdir(self, dir_path):
        url = f"{self.BASE_URL}/1/clouddrive/file"
        querystring = {"pr": "ucpro", "fr": "pc", "uc_param_str": ""}
        payload = {
            "pdir_fid": "0",
            "file_name": "",
            "dir_path": dir_path,
            "dir_init_lock": False,
        }
        response = self._send_request(
            "POST", url, json=payload, params=querystring
        ).json()
        return response

    def rename(self, fid, file_name):
        url = f"{self.BASE_URL}/1/clouddrive/file/rename"
        querystring = {"pr": "ucpro", "fr": "pc", "uc_param_str": ""}
        payload = {"fid": fid, "file_name": file_name}
        response = self._send_request(
            "POST", url, json=payload, params=querystring
        ).json()
        return response

    def delete(self, filelist):
        url = f"{self.BASE_URL}/1/clouddrive/file/delete"
        querystring = {"pr": "ucpro", "fr": "pc", "uc_param_str": ""}
        payload = {"action_type": 2, "filelist": filelist, "exclude_fids": []}
        response = self._send_request(
            "POST", url, json=payload, params=querystring
        ).json()
        return response

    def recycle_list(self, page=1, size=30):
        url = f"{self.BASE_URL}/1/clouddrive/file/recycle/list"
        querystring = {
            "_page": page,
            "_size": size,
            "pr": "ucpro",
            "fr": "pc",
            "uc_param_str": "",
        }
        response = self._send_request("GET", url, params=querystring).json()
        return response["data"]["list"]

    def recycle_remove(self, record_list):
        url = f"{self.BASE_URL}/1/clouddrive/file/recycle/remove"
        querystring = {"uc_param_str": "", "fr": "pc", "pr": "ucpro"}
        payload = {
            "select_mode": 2,
            "record_list": record_list,
        }
        response = self._send_request(
            "POST", url, json=payload, params=querystring
        ).json()
        return response

    # ↑ 请求函数
    # ↓ 操作函数

    # 魔法正则匹配
    def magic_regex_func(self, pattern, replace, taskname=None):
        magic_regex = CONFIG_DATA.get("magic_regex") or MAGIC_REGEX or {}
        keyword = pattern
        if keyword in magic_regex:
            pattern = magic_regex[keyword]["pattern"]
            if replace == "":
                replace = magic_regex[keyword]["replace"]
        if taskname:
            replace = replace.replace("$TASKNAME", taskname)
        return pattern, replace

    def get_id_from_url(self, url):
        url = url.replace("https://pan.quark.cn/s/", "")
        pattern = r"(\w+)(\?pwd=(\w+))?(#/list/share.*/(\w+))?"
        match = re.search(pattern, url)
        if match:
            pwd_id = match.group(1)
            passcode = match.group(3) if match.group(3) else ""
            pdir_fid = match.group(5) if match.group(5) else 0
            return pwd_id, passcode, pdir_fid
        else:
            return None

    def update_savepath_fid(self, tasklist):
        dir_paths = [
            re.sub(r"/{2,}", "/", f"/{item['savepath']}")
            for item in tasklist
            if not item.get("enddate")
            or (
                datetime.now().date()
                <= datetime.strptime(item["enddate"], "%Y-%m-%d").date()
            )
        ]
        if not dir_paths:
            return False
        dir_paths_exist_arr = self.get_fids(dir_paths)
        dir_paths_exist = [item["file_path"] for item in dir_paths_exist_arr]
        # 比较创建不存在的
        dir_paths_unexist = list(set(dir_paths) - set(dir_paths_exist) - set(["/"]))
        for dir_path in dir_paths_unexist:
            mkdir_return = self.mkdir(dir_path)
            if mkdir_return["code"] == 0:
                new_dir = mkdir_return["data"]
                dir_paths_exist_arr.append(
                    {"file_path": dir_path, "fid": new_dir["fid"]}
                )
                print(f"创建文件夹：{dir_path}")
            else:
                print(f"创建文件夹：{dir_path} 失败, {mkdir_return['message']}")
        # 储存目标目录的fid
        for dir_path in dir_paths_exist_arr:
            self.savepath_fid[dir_path["file_path"]] = dir_path["fid"]
        # print(dir_paths_exist_arr)

    def do_save_check(self, shareurl, savepath):
        try:
            pwd_id, passcode, pdir_fid = self.get_id_from_url(shareurl)
            is_sharing, stoken = self.get_stoken(pwd_id, passcode)
            share_file_list = self.get_detail(pwd_id, stoken, pdir_fid)["list"]
            fid_list = [item["fid"] for item in share_file_list]
            fid_token_list = [item["share_fid_token"] for item in share_file_list]
            file_name_list = [item["file_name"] for item in share_file_list]
            if not fid_list:
                return
            get_fids = self.get_fids([savepath])
            to_pdir_fid = (
                get_fids[0]["fid"] if get_fids else self.mkdir(savepath)["data"]["fid"]
            )
            save_file = self.save_file(
                fid_list, fid_token_list, to_pdir_fid, pwd_id, stoken
            )
            if save_file["code"] == 41017:
                return
            elif save_file["code"] == 0:
                dir_file_list = self.ls_dir(to_pdir_fid)
                del_list = [
                    item["fid"]
                    for item in dir_file_list
                    if (item["file_name"] in file_name_list)
                    and ((datetime.now().timestamp() - item["created_at"]) < 60)
                ]
                if del_list:
                    self.delete(del_list)
                    recycle_list = self.recycle_list()
                    record_id_list = [
                        item["record_id"]
                        for item in recycle_list
                        if item["fid"] in del_list
                    ]
                    self.recycle_remove(record_id_list)
                return save_file
            else:
                return False
        except Exception as e:
            if os.environ.get("DEBUG") == True:
                print(f"转存测试失败: {str(e)}")

    def do_save_task(self, task):
        # 判断资源失效记录
        if task.get("shareurl_ban"):
            print(f"《{task['taskname']}》：{task['shareurl_ban']}")
            return

        # 链接转换所需参数
        pwd_id, passcode, pdir_fid = self.get_id_from_url(task["shareurl"])
        # print("match: ", pwd_id, pdir_fid)

        # 获取stoken，同时可验证资源是否失效
        is_sharing, stoken = self.get_stoken(pwd_id, passcode)
        if not is_sharing:
            add_notify(f"❌《{task['taskname']}》：{stoken}\n")
            task["shareurl_ban"] = stoken
            return
        # print("stoken: ", stoken)

        updated_tree = self.dir_check_and_save(task, pwd_id, stoken, pdir_fid)
        if updated_tree.size(1) > 0:
            add_notify(f"✅《{task['taskname']}》添加：\n{updated_tree}")
            return updated_tree
        else:
            add_notify(f"任务结束：没有新的转存任务")
            return False

    def dir_check_and_save(self, task, pwd_id, stoken, pdir_fid="", subdir_path=""):
        tree = Tree()
        # 获取分享文件列表
        share_file_list = self.get_detail(pwd_id, stoken, pdir_fid)["list"]
        # print("share_file_list: ", share_file_list)

        if not share_file_list:
            if subdir_path == "":
                task["shareurl_ban"] = "分享为空，文件已被分享者删除"
                add_notify(f"❌《{task['taskname']}》：{task['shareurl_ban']}\n")
            return tree
        # elif (
        #     len(share_file_list) == 1
        #     and share_file_list[0]["dir"]
        #     and subdir_path == ""
        # ):  # 仅有一个文件夹
        #     print("🧠 该分享是一个文件夹，读取文件夹内列表")
        #     share_file_list = self.get_detail(
        #         pwd_id, stoken, share_file_list[0]["fid"]
        #     )["list"]

        # 获取目标目录文件列表
        savepath = re.sub(r"/{2,}", "/", f"/{task['savepath']}{subdir_path}")
        if not self.savepath_fid.get(savepath):
            if get_fids := self.get_fids([savepath]):
                self.savepath_fid[savepath] = get_fids[0]["fid"]
            else:
                print(f"❌ 目录 {savepath} fid获取失败，跳过转存")
                return tree
        to_pdir_fid = self.savepath_fid[savepath]
        dir_file_list = self.ls_dir(to_pdir_fid)
        # print("dir_file_list: ", dir_file_list)

        tree.create_node(
            savepath,
            pdir_fid,
            data={
                "is_dir": True,
            },
        )

        # 需保存的文件清单
        need_save_list = []
        # 添加符合的
        for share_file in share_file_list:
            if share_file["dir"] and task.get("update_subdir", False):
                pattern, replace = task["update_subdir"], ""
            else:
                pattern, replace = self.magic_regex_func(
                    task["pattern"], task["replace"], task["taskname"]
                )
            # 正则文件名匹配
            if re.search(pattern, share_file["file_name"]):
                # 替换后的文件名
                save_name = (
                    re.sub(pattern, replace, share_file["file_name"])
                    if replace != ""
                    else share_file["file_name"]
                )
                # 忽略后缀
                if task.get("ignore_extension") and not share_file["dir"]:
                    compare_func = lambda a, b1, b2: (
                        os.path.splitext(a)[0] == os.path.splitext(b1)[0]
                        or os.path.splitext(a)[0] == os.path.splitext(b2)[0]
                    )
                else:
                    compare_func = lambda a, b1, b2: (a == b1 or a == b2)
                # 判断目标目录文件是否存在
                file_exists = any(
                    compare_func(
                        dir_file["file_name"], share_file["file_name"], save_name
                    )
                    for dir_file in dir_file_list
                )
                if not file_exists:
                    share_file["save_name"] = save_name
                    need_save_list.append(share_file)
                elif share_file["dir"]:
                    # 存在并是一个文件夹
                    if task.get("update_subdir", False):
                        if re.search(task["update_subdir"], share_file["file_name"]):
                            print(f"检查子文件夹：{savepath}/{share_file['file_name']}")
                            subdir_tree = self.dir_check_and_save(
                                task,
                                pwd_id,
                                stoken,
                                share_file["fid"],
                                f"{subdir_path}/{share_file['file_name']}",
                            )
                            if subdir_tree.size(1) > 0:
                                # 合并子目录树
                                tree.create_node(
                                    "📁" + share_file["file_name"],
                                    share_file["fid"],
                                    parent=pdir_fid,
                                    data={
                                        "is_dir": share_file["dir"],
                                    },
                                )
                                tree.merge(share_file["fid"], subdir_tree, deep=False)
            # 指定文件开始订阅/到达指定文件（含）结束历遍
            if share_file["fid"] == task.get("startfid", ""):
                break

        fid_list = [item["fid"] for item in need_save_list]
        fid_token_list = [item["share_fid_token"] for item in need_save_list]
        if fid_list:
            save_file_return = self.save_file(
                fid_list, fid_token_list, to_pdir_fid, pwd_id, stoken
            )
            err_msg = None
            if save_file_return["code"] == 0:
                task_id = save_file_return["data"]["task_id"]
                query_task_return = self.query_task(task_id)
                if query_task_return["code"] == 0:
                    # 建立目录树
                    for index, item in enumerate(need_save_list):
                        icon = (
                            "📁"
                            if item["dir"] == True
                            else "🎞️" if item["obj_category"] == "video" else ""
                        )
                        tree.create_node(
                            f"{icon}{item['save_name']}",
                            item["fid"],
                            parent=pdir_fid,
                            data={
                                "fid": f"{query_task_return['data']['save_as']['save_as_top_fids'][index]}",
                                "path": f"{savepath}/{item['save_name']}",
                                "is_dir": item["dir"],
                            },
                        )
                else:
                    err_msg = query_task_return["message"]
            else:
                err_msg = save_file_return["message"]
            if err_msg:
                add_notify(f"❌《{task['taskname']}》转存失败：{err_msg}\n")
        return tree

    def do_rename_task(self, task, subdir_path=""):
        pattern, replace = self.magic_regex_func(
            task["pattern"], task["replace"], task["taskname"]
        )
        if not pattern or not replace:
            return 0
        savepath = re.sub(r"/{2,}", "/", f"/{task['savepath']}{subdir_path}")
        if not self.savepath_fid.get(savepath):
            self.savepath_fid[savepath] = self.get_fids([savepath])[0]["fid"]
        dir_file_list = self.ls_dir(self.savepath_fid[savepath])
        dir_file_name_list = [item["file_name"] for item in dir_file_list]
        is_rename_count = 0
        for dir_file in dir_file_list:
            if dir_file["dir"]:
                is_rename_count += self.do_rename_task(
                    task, f"{subdir_path}/{dir_file['file_name']}"
                )
            if re.search(pattern, dir_file["file_name"]):
                save_name = (
                    re.sub(pattern, replace, dir_file["file_name"])
                    if replace != ""
                    else dir_file["file_name"]
                )
                if save_name != dir_file["file_name"] and (
                    save_name not in dir_file_name_list
                ):
                    rename_return = self.rename(dir_file["fid"], save_name)
                    if rename_return["code"] == 0:
                        print(f"重命名：{dir_file['file_name']} → {save_name}")
                        is_rename_count += 1
                    else:
                        print(
                            f"重命名：{dir_file['file_name']} → {save_name} 失败，{rename_return['message']}"
                        )
        return is_rename_count > 0


def verify_account(account):
    # 验证账号
    print(f"▶️ 验证第{account.index}个账号")
    if "__uid" not in account.cookie:
        print(f"💡 不存在cookie必要参数，判断为仅签到")
        return False
    else:
        account_info = account.init()
        if not account_info:
            add_notify(f"👤 第{account.index}个账号登录失败，cookie无效❌")
            return False
        else:
            print(f"👤 账号昵称: {account_info['nickname']}✅")
            return True


def format_bytes(size_bytes: int) -> str:
    units = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = 0
    while size_bytes >= 1024 and i < len(units) - 1:
        size_bytes /= 1024
        i += 1
    return f"{size_bytes:.2f} {units[i]}"


def do_sign(account):
    if not account.mparam:
        print("⏭️ 移动端参数未设置，跳过签到")
        print()
        return
    # 每日领空间
    growth_info = account.get_growth_info()
    if growth_info:
        growth_message = f"💾 {'88VIP' if growth_info['88VIP'] else '普通用户'} 总空间：{format_bytes(growth_info['total_capacity'])}，签到累计获得：{format_bytes(growth_info['cap_composition'].get('sign_reward', 0))}"
        if growth_info["cap_sign"]["sign_daily"]:
            sign_message = f"📅 签到记录: 今日已签到+{int(growth_info['cap_sign']['sign_daily_reward']/1024/1024)}MB，连签进度({growth_info['cap_sign']['sign_progress']}/{growth_info['cap_sign']['sign_target']})✅"
            message = f"{sign_message}\n{growth_message}"
            print(message)
        else:
            sign, sign_return = account.get_growth_sign()
            if sign:
                sign_message = f"📅 执行签到: 今日签到+{int(sign_return/1024/1024)}MB，连签进度({growth_info['cap_sign']['sign_progress']+1}/{growth_info['cap_sign']['sign_target']})✅"
                message = f"{sign_message}\n{growth_message}"
                if (
                    str(
                        CONFIG_DATA.get("push_config", {}).get("QUARK_SIGN_NOTIFY")
                    ).lower()
                    == "false"
                    or os.environ.get("QUARK_SIGN_NOTIFY") == "false"
                ):
                    print(message)
                else:
                    message = message.replace("今日", f"[{account.nickname}]今日")
                    add_notify(message)
            else:
                print(f"📅 签到异常: {sign_return}")


def do_save(account, tasklist=[]):
    add_notify(f"转存账号: {account.nickname}")
    # 获取全部保存目录fid
    account.update_savepath_fid(tasklist)

    # 执行任务
    for index, task in enumerate(tasklist):
        add_notify(f"任务名称: {task['taskname']}")
        add_notify(f"分享链接: {task['shareurl']}")
        add_notify(f"保存路径: {task['savepath']}")
        account.do_save_task(task)
        account.do_rename_task(task)
        
    return NOTIFYS    
