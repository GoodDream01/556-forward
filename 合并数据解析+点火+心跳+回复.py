import socket
import binascii
import logging
import threading
import time
import requests
from flask import Flask, request, jsonify

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)

# 全局配置
HEARTBEAT_MESSAGE = "7B01001631313131313131313131310000000000007B"  # 心跳包
REPLY_HEARTBEAT = "7B81001031313131313131313131317B"  # 平台回复心跳
FIRE_COMMAND = "7B09001031313131313131313131317B2423303030344A463030333030314242"  # 即时点火指令
QUERY_SMOKESTATE_COMMAND = "7B09001031313131313131313131317B2423303030345943303031304242"  # 查询烟炉状态指令
LOAD_SMOKESTICK_COMMAND = "7B09001031313131313131313131317B242330303034595A3030333939364242"  # 装载烟条指令
UNLOAD_SMOKESTICK_COMMAND = "7B09001031313131313131313131317B24233030303459583030333939364242"  # 卸载烟条指令
SET_SYSTEM_TIME_COMMAND_PREFIX = "7B09001031313131313131313131317B2423303030345853303132"   # 系统时间设置指令
HEARTBEAT_IP = "182.92.85.227"
HEARTBEAT_PORT = 5023
HEARTBEAT_INTERVAL = 30  # 心跳间隔时间，单位：秒
API_URL = "http://back.gs3.pancoit.com/api/msg/normal"
HEADERS = {
    'Content-Type': 'application/json',
    'Authorization': 'eyJhbGciOiJIUzUxMiJ9.eyJleHAiOjI2MjczNTU5ODAsInN1YiI6IjI3ODU5RjNCQTE0MDRCRUQ5Rjg2REZDRTQ3REYwRTcwIiwiaWF0IjoxNjgxMjc1OTgwfQ.8YWWJ9blKf3R-j2l7W2LRvAirPqbfMYgBZTc065_o502xF0SU0lIv19MbKSVCZsf09-zg-IIwrP7qwM9p42Pfg'
}

# BCC校验计算
def calculate_bcc(data):
    """
    计算BCC校验码
    """
    bcc = 0
    for byte in data:
        bcc ^= ord(byte)
    return f"{bcc:02X}"

# 心跳包发送函数
# 心跳包发送函数（改进指令判断逻辑）
def send_heartbeat():
    """
    定时发送心跳包并监听平台回复
    """
    while True:
        try:
            udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            udp_socket.settimeout(8)  # 设置超时时间

            # 发送心跳包
            udp_socket.sendto(binascii.unhexlify(HEARTBEAT_MESSAGE), (HEARTBEAT_IP, HEARTBEAT_PORT))
            logging.info(f"成功发送心跳包到 {HEARTBEAT_IP}:{HEARTBEAT_PORT}")

            # 接收平台回复
            response, addr = udp_socket.recvfrom(2048)
            response_hex = response.hex().upper()
            logging.info(f"接收到平台回复: {response_hex}")

            if response_hex == REPLY_HEARTBEAT:
                logging.info("收到平台回复心跳，等待平台指令...")
                # 等待具体指令
                response, addr = udp_socket.recvfrom(2048)
                response_hex = response.hex().upper()
                logging.info(f"接收到平台指令: {response_hex}")

                # 判断指令并调用对应函数
                if response_hex == FIRE_COMMAND:
                    handle_instant_fire()
                elif response_hex == QUERY_SMOKESTATE_COMMAND:
                    handle_query_smoke_state()
                elif response_hex == LOAD_SMOKESTICK_COMMAND:
                    handle_load_smokestick()
                elif response_hex == UNLOAD_SMOKESTICK_COMMAND:
                    handle_unload_smokestick()
                elif response_hex.startswith(SET_SYSTEM_TIME_COMMAND_PREFIX[:40]):  # 前缀匹配系统时间设置指令
                    logging.info("检测到 ‘系统时间设置’ 指令")
                    handle_set_system_time()
                else:
                    logging.warning(f"收到未知指令: {response_hex}")

        except socket.timeout:
            logging.warning("未收到平台回复，继续发送心跳包。")
        except Exception as e:
            logging.error(f"心跳包或指令处理失败: {e}")
        finally:
            udp_socket.close()
        time.sleep(HEARTBEAT_INTERVAL)





# 即时点火指令
def handle_instant_fire():
    """
    处理即时点火指令，向 API 发送 JSON 数据
    """
    logging.info("处理 ‘即时点火’ 指令...")
    data = {
        "groupName": "bdcivil",
        "portname": "NULL",
        "toAddr": 12524002,  # 请使用实际的值
        "content": "00",
        "msgId": "123456"
    }
    try:
        response = requests.post(API_URL, json=data, headers=HEADERS)
        if response.status_code == 200:
            response_data = response.json()
            if response_data.get("code") == 0:
                logging.info(f"‘即时点火’ 数据发送成功: {data}")
            else:
                logging.error(f"‘即时点火’ 数据发送失败，返回内容: {response_data}")
        else:
            logging.error(f"发送 ‘即时点火’ 数据失败，状态码: {response.status_code}, 响应: {response.text}")
    except Exception as e:
        logging.error(f"‘即时点火’ 请求失败: {e}")

# 查询烟炉状态指令
def handle_query_smoke_state():
    """
    处理查询烟炉状态指令，向 API 发送 JSON 数据
    """
    logging.info("处理‘ 查询烟炉状态’ 指令...")
    data = {
        "groupName": "bdcivil",
        "portname": "NULL",
        "toAddr": 12524002,  # 请使用实际的值
        "content": "0f",
        "msgId": "123456"
    }
    try:
        response = requests.post(API_URL, json=data, headers=HEADERS)
        if response.status_code == 200:
            logging.info(f"成功发送 ‘查询烟炉状态’ 数据到 {API_URL}: {data}")
        else:
            logging.error(f"发送 ‘查询烟炉状态’ 数据失败，状态码: {response.status_code}, 响应: {response.text}")
    except Exception as e:
        logging.error(f"‘查询烟炉状态’ 请求失败: {e}")

# 装载烟条指令
def handle_load_smokestick():
    """
    处理装载烟条指令，向 API 发送 JSON 数据
    """
    logging.info("处理 ‘装载烟条’ 指令...")
    data = {
        "groupName": "bdcivil",
        "portname": "NULL",
        "toAddr": 12524002,  # 请使用实际的值
        "content": "0e",
        "msgId": "123456"
    }
    try:
        response = requests.post(API_URL, json=data, headers=HEADERS)
        if response.status_code == 200:
            logging.info(f"成功发送 ‘装载烟条’ 数据到 {API_URL}: {data}")
        else:
            logging.error(f"发送 ‘装载烟条’ 数据失败，状态码: {response.status_code}, 响应: {response.text}")
    except Exception as e:
        logging.error(f"‘装载烟条’ 请求失败: {e}")

# 卸载烟条指令
def handle_unload_smokestick():
    """
    处理卸载烟条指令，向 API 发送 JSON 数据
    """
    logging.info("处理 ‘卸载烟条’ 指令...")
    data = {
        "groupName": "bdcivil",
        "portname": "NULL",
        "toAddr": 12524002,  # 请使用实际的值
        "content": "0d",
        "msgId": "123456"
    }
    try:
        response = requests.post(API_URL, json=data, headers=HEADERS)
        if response.status_code == 200:
            logging.info(f"成功发送 ‘卸载烟条’ 数据到 {API_URL}: {data}")
        else:
            logging.error(f"发送 ‘卸载烟条’ 数据失败，状态码: {response.status_code}, 响应: {response.text}")
    except Exception as e:
        logging.error(f"‘卸载烟条’ 请求失败: {e}")

# 系统时间设置指令
def handle_set_system_time():
    """
    处理系统时间设置指令
    """
    logging.info("处理系统时间设置指令...")
    data = {
        "groupName": "bdcivil",
        "portname": "NULL",
        "toAddr": 12524002,
        "content": "0c",
        "msgId": "123456"
    }
    try:
        response = requests.post(API_URL, json=data, headers=HEADERS)
        if response.status_code == 200:
            response_data = response.json()
            if response_data.get("code") == 0:
                logging.info(f"系统时间设置数据发送成功: {data}")
            else:
                logging.error(f"系统时间设置数据发送失败，返回内容: {response_data}")
        else:
            logging.error(f"发送系统时间设置数据失败，状态码: {response.status_code}, 响应: {response.text}")
    except Exception as e:
        logging.error(f"系统时间设置请求失败: {e}")




# 处理接收到的 content 字段
def process_content(content):
    """
    解析 content 字段，生成并返回需要转发的最终报文
    """
    # 解析 HEX 数据为 ASCII
    received_ascii = binascii.unhexlify(content).decode("ascii")
    #logging.info(f"接收到的ASCII数据: {received_ascii}")

    # 分析并提取字段
    header = received_ascii[:8]  # $#0001TB
    data_length = int(received_ascii[8:11])  # 数据长度
    main_content = received_ascii[11:-2]  # 数据段
    checksum = received_ascii[-2:]  # 校验位

    # 分割内容
    time_field = main_content[:12]  # 时间字段
    smoke_group_1 = main_content[12:40]  # 第一组烟炉状态
    smoke_group_3 = main_content[40:68]  # 第三组烟炉状态
    remaining_data = main_content[68:]  # 后续字段

    # 插入需要的烟炉数据
    new_smoke_data = "DDDDDDDDDDDDDDDDDDDDDDDDDDDD"  # 新的烟炉数据
    updated_main_content = time_field + smoke_group_1 + new_smoke_data + smoke_group_3 + remaining_data

    # 重新计算数据长度
    new_data_length = len(updated_main_content)
    formatted_data_length = f"{new_data_length:03d}"  # 转为3位长度字符串

    # 拼接新的报文
    new_report = f"{header}{formatted_data_length}{updated_main_content}"

    # 计算新的校验位
    new_checksum = calculate_bcc(new_report)

    # 拼接最终报文
    final_report = f"{new_report}{new_checksum}"
    logging.info(f"生成的最终报文: {final_report}")

    # 转换为 HEX，并在前面添加固定数据8
    fixed_prefix = "7B09001031313131313131313131317B"
    final_hex_report = fixed_prefix + binascii.hexlify(final_report.encode("ascii")).decode("ascii")
    return final_hex_report

# 转发数据到 UDP 服务器
def forward_to_udp_server(final_hex_report, ip_address="182.92.85.227", port=5023):
    """
    将 HEX 格式数据通过 UDP 协议发送并接收回复
    """
    try:
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_socket.settimeout(10)  # 设置超时时间为 5 秒
        udp_socket.sendto(binascii.unhexlify(final_hex_report), (ip_address, port))
        logging.info(f"成功发送报文到 {ip_address}:{port}")

        # 接收回复
        response, addr = udp_socket.recvfrom(2048)  # 接收最多 1024 字节的数据
        logging.info(f"接收到来自 {addr} 的回复: {response.hex()}")

    except socket.timeout:
        logging.warning("UDP 接收超时，未收到服务器回复。")
    except Exception as e:
        logging.error(f"UDP 转发失败: {e}")
    finally:
        udp_socket.close()


# 接收 POST 请求并提取 content 字段
# @app.route('/api/data/rv', methods=['POST'])
# def receive_data():
#     data = request.json
#     logging.info(f"接收到的数据: {data}")
#
#     if 'commInfos' in data:
#         for item in data['commInfos']:
#             content = item.get('content')  # 获取 HEX 数据
#             if content:
#                 try:
#                     # 去除空格
#                     cleaned_content = content.replace(" ", "")
#
#                     # 将 HEX 转换为 ASCII
#                     ascii_data = binascii.unhexlify(cleaned_content).decode('ascii')
#
#                     # 处理数据并生成最终报文
#                     final_hex_report = process_content(cleaned_content)
#                     logging.info(f"最终需转发的 HEX 数据: {final_hex_report}")
#
#                     # 转发数据
#                     forward_to_udp_server(final_hex_report)
#
#                 except (binascii.Error, UnicodeDecodeError) as e:
#                     logging.error(f"处理数据失败: {e}")
#                     return jsonify({"status": "error", "message": "Invalid HEX data"}), 400
#     return jsonify({"status": "200"}), 200

# 启动心跳线程

@app.route('/api/data/rv', methods=['POST'])
def receive_data():
    """
    接收数据并即时返回状态 200
    """
    data = request.json
    logging.info(f"接收到的数据: {data}")

    if 'commInfos' in data:
        for item in data['commInfos']:
            content = item.get('content')  # 获取 HEX 数据

            # 验证 content 是否存在
            if not content:
                logging.warning(f"缺少 content 字段: {item}")
                continue  # 跳过此条记录

            try:
                # 去除空格
                cleaned_content = content.replace(" ", "")

                # 将 HEX 转换为 ASCII
                ascii_data = binascii.unhexlify(cleaned_content).decode('ascii')

                # 处理数据并生成最终报文
                final_hex_report = process_content(cleaned_content)
                logging.info(f"最终需转发的 HEX 数据: {final_hex_report}")

                # 异步转发数据
                threading.Thread(target=forward_to_udp_server, args=(final_hex_report,)).start()

            except (binascii.Error, UnicodeDecodeError) as e:
                # 捕获 HEX 数据解析或解码错误
                logging.error(f"处理数据失败: {e} - content: {content}")
                continue  # 跳过此条记录

            except Exception as e:
                # 捕获其他异常
                logging.error(f"处理数据时发生异常: {e}")
                continue  # 跳过此条记录

    # 返回状态 200，立即响应
    return jsonify({"status": "200"}), 200


def start_heartbeat_thread():
    """
    启动心跳线程
    """
    heartbeat_thread = threading.Thread(target=send_heartbeat, daemon=True)
    heartbeat_thread.start()
    logging.info("心跳线程已启动。")

if __name__ == '__main__':
    logging.info("启动程序...")
    start_heartbeat_thread()

    # 启动 Flask 应用
    app.run(debug=True, host="0.0.0.0", port=7000, threaded=True)
