import os, json

config_path = "plugins/Quark/quark_config.json"


class Config:
    _config_data = {}

    def __init__(self):
        self._config_data = self.get_all()

    def get_all(self):
        if not os.path.exists(config_path):
            with open(config_path, "w") as file:
                file.write("{}")
            return {}
        else:
            print(f"⚙️ 正从 {config_path} 文件中读取配置")
            with open(config_path, "r", encoding="utf-8") as file:
                config_data = json.load(file)
            return config_data

    def get_config(self, key):
        return self._config_data.get(key)

    def set_config(self, key, task):
        self._config_data[key] = task
        self.save_config()

    def set_all_config(self, tasks):
        self._config_data = tasks
        self.save_config()

    def save_config(self):
        with open(config_path, "w") as file:
            file.write(json.dumps(self._config_data))
