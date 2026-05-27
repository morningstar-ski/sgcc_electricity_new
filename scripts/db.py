import logging
import os

import sqlite3

class DB:
    def connect_user_db(self, user_id):
        # 连接用户数据库的逻辑
        pass
    def insert_data(self, data:dict):
        # 向数据库插入数据的逻辑
        pass
    def insert_expand_data(self, data:dict):
        # 向数据库插入扩展数据的逻辑
        pass
    def close_connect(self):
        # 关闭连接
        pass

class SqliteDB(DB):
    def connect_user_db(self, user_id):
        """创建数据库集合，db_name = electricity_daily_usage_{user_id}
        :param user_id: 用户ID"""
        try:
            # 创建数据库
            DB_NAME = os.getenv("DB_NAME", "homeassistant.db")
            if 'PYTHON_IN_DOCKER' in os.environ:
                DB_NAME = "/data/" + DB_NAME
            self.connect = sqlite3.connect(DB_NAME)
            self.connect.cursor()
            logging.info(f"数据库 {DB_NAME} 创建成功。")
            self.user_id = user_id
            # 创建表名
            self.table_name = f"daily{user_id}"
            sql = f'''CREATE TABLE IF NOT EXISTS {self.table_name} (
                    date DATE PRIMARY KEY NOT NULL,
                    usage REAL NOT NULL)'''
            self.connect.execute(sql)
            logging.info(f"数据表 {self.table_name} 创建成功")

				# 创建data表名
            self.table_expand_name = f"data{user_id}"
            sql = f'''CREATE TABLE IF NOT EXISTS {self.table_expand_name} (
                    name TEXT PRIMARY KEY NOT NULL,
                    value TEXT NOT NULL)'''
            self.connect.execute(sql)
            logging.info(f"数据表 {self.table_expand_name} 创建成功")

            self.connect.execute('''CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY NOT NULL,
                    phone_number TEXT,
                    user_name TEXT,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)''')
            self.connect.execute(f'''CREATE TABLE IF NOT EXISTS balance{user_id} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    logged_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    balance REAL,
                    as_of TEXT,
                    amount_due REAL,
                    user_name TEXT)''')
            self.connect.execute(f'''CREATE TABLE IF NOT EXISTS monthly{user_id} (
                    month TEXT PRIMARY KEY NOT NULL,
                    total_usage REAL,
                    total_charge REAL,
                    valley_usage REAL,
                    flat_usage REAL,
                    peak_usage REAL,
                    tip_usage REAL,
                    user_name TEXT)''')
            self.connect.execute(f'''CREATE TABLE IF NOT EXISTS yearly{user_id} (
                    year TEXT PRIMARY KEY NOT NULL,
                    total_usage REAL,
                    total_charge REAL,
                    user_name TEXT)''')
            self.connect.execute(f'''CREATE TABLE IF NOT EXISTS daily_detail{user_id} (
                    date DATE PRIMARY KEY NOT NULL,
                    total_usage REAL,
                    valley_usage REAL,
                    flat_usage REAL,
                    peak_usage REAL,
                    tip_usage REAL,
                    user_name TEXT)''')
            self.connect.commit()

        # 如果表已存在，则不会创建
        except sqlite3.Error as e:
            logging.debug(f"创建数据库或数据表错误: {e}")
            return False
        return True

    def insert_data(self, data:dict):
        if self.connect is None:
            logging.error("数据库连接未建立。")
            return
        # 创建索引
        try:
            sql = f"INSERT OR REPLACE INTO {self.table_name} VALUES(strftime('%Y-%m-%d','{data['date']}'),{data['usage']});"
            self.connect.execute(sql)
            self.connect.commit()
        except BaseException as e:
            logging.debug(f"数据更新失败: {e}")

    def insert_expand_data(self, data:dict):
        if self.connect is None:
            logging.error("数据库连接未建立。")
            return
        # 创建索引
        try:
            sql = f"INSERT OR REPLACE INTO {self.table_expand_name} VALUES('{data['name']}','{data['value']}');"
            self.connect.execute(sql)
            self.connect.commit()
        except BaseException as e:
            logging.debug(f"数据更新失败: {e}")

    def upsert_user(self, user_id: str, phone_number: str, user_name: str = ""):
        try:
            self.connect.execute(
                "INSERT OR REPLACE INTO users(user_id, phone_number, user_name, updated_at) VALUES(?, ?, ?, CURRENT_TIMESTAMP)",
                (user_id, phone_number, user_name),
            )
            self.connect.commit()
            return True
        except sqlite3.Error as e:
            logging.error(f"用户信息更新失败: {e}")
            return False

    def insert_balance_log(self, data: dict):
        try:
            self.connect.execute(
                f"INSERT INTO balance{self.user_id}(balance, as_of, amount_due, user_name) VALUES(?, ?, ?, ?)",
                (
                    data.get("balance"),
                    data.get("as_of"),
                    data.get("amount_due"),
                    data.get("user_name", ""),
                ),
            )
            self.connect.commit()
            return True
        except sqlite3.Error as e:
            logging.error(f"余额日志写入失败: {e}")
            return False

    def insert_daily_data(self, data: dict):
        try:
            total_usage = data.get("total_usage", data.get("usage"))
            self.connect.execute(
                f"""INSERT OR REPLACE INTO daily_detail{self.user_id}
                    (date, total_usage, valley_usage, flat_usage, peak_usage, tip_usage, user_name)
                    VALUES(strftime('%Y-%m-%d', ?), ?, ?, ?, ?, ?, ?)""",
                (
                    data.get("date"),
                    total_usage,
                    data.get("valley_usage"),
                    data.get("flat_usage"),
                    data.get("peak_usage"),
                    data.get("tip_usage"),
                    data.get("user_name", ""),
                ),
            )
            if total_usage is not None:
                self.insert_data({"date": data.get("date"), "usage": total_usage})
            self.connect.commit()
            return True
        except sqlite3.Error as e:
            logging.error(f"日用电数据写入失败: {e}")
            return False

    def insert_monthly_data(self, data: dict):
        try:
            self.connect.execute(
                f"""INSERT OR REPLACE INTO monthly{self.user_id}
                    (month, total_usage, total_charge, valley_usage, flat_usage, peak_usage, tip_usage, user_name)
                    VALUES(?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    data.get("month"),
                    data.get("total_usage"),
                    data.get("total_charge"),
                    data.get("valley_usage"),
                    data.get("flat_usage"),
                    data.get("peak_usage"),
                    data.get("tip_usage"),
                    data.get("user_name", ""),
                ),
            )
            self.connect.commit()
            return True
        except sqlite3.Error as e:
            logging.error(f"月度数据写入失败: {e}")
            return False

    def insert_yearly_data(self, data: dict):
        try:
            self.connect.execute(
                f"INSERT OR REPLACE INTO yearly{self.user_id}(year, total_usage, total_charge, user_name) VALUES(?, ?, ?, ?)",
                (
                    data.get("year"),
                    data.get("total_usage"),
                    data.get("total_charge"),
                    data.get("user_name", ""),
                ),
            )
            self.connect.commit()
            return True
        except sqlite3.Error as e:
            logging.error(f"年度数据写入失败: {e}")
            return False

    def cleanup_old_data(self):
        try:
            retention_days = int(os.getenv("DATA_RETENTION_DAYS", 7))
            self.connect.execute(
                f"DELETE FROM {self.table_name} WHERE date < date('now', ?)",
                (f"-{retention_days} days",),
            )
            self.connect.execute(
                f"DELETE FROM daily_detail{self.user_id} WHERE date < date('now', ?)",
                (f"-{retention_days} days",),
            )
            self.connect.commit()
            return True
        except (ValueError, sqlite3.Error) as e:
            logging.warning(f"历史数据清理失败: {e}")
            return False

    def close_connect(self):
        if self.connect:
            self.connect.close()
            self.connect = None
            logging.info("数据库连接已关闭。")

class MysqlDB(DB):
    def connect_user_db(self, user_id):
        try:
            import mysql.connector

            host = os.getenv("MYSQL_HOST")
            user = os.getenv("MYSQL_USER")
            password = os.getenv("MYSQL_PASSWORD")
            database = os.getenv("MYSQL_DATABASE")
            port = int(os.getenv("MYSQL_PORT", 3306))
            self.connect = mysql.connector.connect(
                host=host,
                user=user,
                password=password,
                database=database,
                port=port
            )

            if self.connect.is_connected():
                logging.info(f"已连接 MySQL 数据库。")
                return self.create_tabe(user_id)
            else:
                logging.error("连接 MySQL 数据库失败。")
                return False
        except BaseException as e:
            logging.error(f"缺少 MySQL 配置: {e}")
            return False

    def create_tabe(self, user_id):
        try:
            cursor = self.connect.cursor()
            # 创建表名
            self.table_name = f"sg_daily_{user_id}"
            sql = f'''CREATE TABLE IF NOT EXISTS `{self.table_name}` (
                    `date` DATE PRIMARY KEY NOT NULL,
                    `usage` REAL NOT NULL)'''
            cursor.execute(sql)
            logging.info(f"数据表 {self.table_name} 创建成功")

            # 创建data表名
            self.table_expand_name = f"sg_data_{user_id}"
            sql = f'''CREATE TABLE IF NOT EXISTS `{self.table_expand_name}` (
                    `name` varchar(100) PRIMARY KEY NOT NULL,
                    `value` TEXT NOT NULL)'''
            cursor.execute(sql)
            logging.info(f"数据表 {self.table_expand_name} 创建成功")
            self.connect.commit()
        except BaseException as e:
            logging.error(f"创建数据表错误: {e}")
            return False
        finally:
            if cursor:
                cursor.close()
        return True

    def insert_data(self, data:dict):
        if self.connect is None:
            logging.error("数据库连接未建立。")
            return
        try:
            cursor = self.connect.cursor()
            sql = f"REPLACE INTO `{self.table_name}` VALUES(str_to_date('{data['date']}', '%Y-%m-%d'),{data['usage']});"
            cursor.execute(sql)
            self.connect.commit()
            return True
        except BaseException as e:
            logging.error(f"数据更新失败: {e}")
        finally:
            if cursor:
                cursor.close()
        return False

    def insert_expand_data(self, data:dict):
        if self.connect is None:
            logging.debug("数据库连接未建立。")
            return
        try:
            cursor = self.connect.cursor()
            sql = f"REPLACE INTO `{self.table_expand_name}` VALUES('{data['name']}','{data['value']}');"
            cursor.execute(sql)
            self.connect.commit()
            return True
        except BaseException as e:
            logging.error(f"数据更新失败: {e}")
        finally:
            if cursor:
                cursor.close()
        return False

    def close_connect(self):
        if self.connect and self.connect.is_connected():
            self.connect.close()
            self.connect = None
            logging.info("MySQL 数据库连接已关闭。")
