#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Project : FWS_M_Debug 
# @Author  : Bxl
# @Date    : 2025/5/14 15:42
import os, sys
from flask import Flask, request, jsonify
import pymysql
from datetime import datetime

app = Flask(__name__)

# 数据库连接配置
db_config = {
    "host": "localhost",
    "user": "root",
    "password": "6909",
    "database": "httpTest",
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor
}

# 数据库插入函数
def insert_comm_info(comm_time, content, from_addr, to_addr):
    connection = pymysql.connect(**db_config)
    try:
        with connection.cursor() as cursor:
            sql = """
            INSERT INTO bdinfo (commTime, content, fromAddr, toAddr)
            VALUES (%s, %s, %s, %s)
            """
            cursor.execute(sql, (comm_time, content, from_addr, to_addr))
        connection.commit()
    finally:
        connection.close()

# 接收POST请求并存储数据
@app.route('/api/data/rv', methods=['POST'])
def receive_data():
    data = request.json
    print("data:",data)
    if 'commInfos' in data:
        for item in data['commInfos']:
            comm_time = item.get('commTime')
            content = item.get('content')
            from_addr = item.get('fromAddr')
            to_addr = item.get('toAddr')

            try:
                parts = content.split(',')
                # parts[-1] 是 "2715*71"，再按 '*' 拆一次
                content = parts[-1].split('*')[0]
            except Exception:
                content = content
            # 数据验证与转换
            if comm_time and content and from_addr and to_addr:
                try:
                    # 将 commTime 转换为 DATETIME 格式
                    comm_time = datetime.strptime(comm_time, '%Y-%m-%d %H:%M:%S')
                    insert_comm_info(comm_time, content, from_addr, to_addr)
                except Exception as e:
                    return jsonify({"status": "error", "message": str(e)}), 400

    return jsonify({"status": "200"}), 200

if __name__ == '__main__':
    # 取当前脚本文件名（带 .py）
    script_name = os.path.basename(sys.argv[0])
    # 在 Windows 下改控制台标题
    os.system(f'title {script_name}')
    app.run(debug=True, host='0.0.0.0', port=6000)
