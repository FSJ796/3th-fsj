"""项目配置包。

使用 PyMySQL 作为 MySQL 驱动，避免在 Windows 上编译 mysqlclient。
"""
import pymysql

# Django 5.2 的 MySQL 后端要求 mysqlclient >= 2.2.3，
# PyMySQL 通过 install_as_MySQLdb 伪装成 MySQLdb，这里同步版本号。
pymysql.version_info = (2, 2, 3, 'final', 0)
pymysql.install_as_MySQLdb()
