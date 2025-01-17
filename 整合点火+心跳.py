import socket
import binascii
import logging
import threading
import time
import requests

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 全局配置
HEARTBEAT_MESSAGE = "7B01001631313131313131313131310000000000007B"  # 心跳包
REPLY_HEARTBEAT = "7B81001031313131313131313131317B"  # 平台回复心跳
FIRE_COMMAND = "7B09001031313131313131313131317B2423303030344A463030333030314242"  # 即时点火指令
QUERY_SMOKESTATE_COMMAND = "7B09001031313131313131313131317B2423303030345943303031304242"  # 查询烟炉状态指令
HEARTBEAT_IP = "182.92.85.227"
HEARTBEAT_PORT = 5023
HEARTBEAT_INTERVAL = 30  # 心跳间隔时间，单位：秒
API_URL = "http://back.gs3.pancoit.com/api/msg/normal"

# 心跳包发送函数
def send_heartbeat():
    """
    定时发送心跳包并监听平台回复
    """
    while True:
        try:
            udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            udp_socket.settimeout(5)  # 设置超时时间

            # 发送心跳包
            udp_socket.sendto(binascii.unhexlify(HEARTBEAT_MESSAGE), (HEARTBEAT_IP, HEARTBEAT_PORT))
            logging.info(f"成功发送心跳包到 {HEARTBEAT_IP}:{HEARTBEAT_PORT}")

            # 接收平台回复
            response, addr = udp_socket.recvfrom(2048)
            response_hex = response.hex().upper()
            logging.info(f"接收到平台回复: {response_hex}")

            if response_hex == REPLY_HEARTBEAT:
                logging.info("收到平台回复心跳，等待平台指令...")
                # 等待指令（即时点火或查询烟炉状态）
                response, addr = udp_socket.recvfrom(2048)
                response_hex = response.hex().upper()
                logging.info(f"接收到平台指令: {response_hex}")

                if response_hex.startswith(FIRE_COMMAND[:40]):  # 即时点火指令
                    handle_instant_fire()
                elif response_hex.startswith(QUERY_SMOKESTATE_COMMAND[:40]):  # 查询烟炉状态指令
                    handle_query_smoke_state()

        except socket.timeout:
            logging.warning("未收到平台回复，继续发送心跳包。")
        except Exception as e:
            logging.error(f"心跳包或指令处理失败: {e}")
        finally:
            udp_socket.close()
        time.sleep(HEARTBEAT_INTERVAL)

# 即时点火逻辑
def handle_instant_fire():
    """
    处理即时点火指令
    """
    logging.info("处理即时点火指令...")
    data = {
        "groupName": "bdcivil",
        "portname": "NULL",
        "toAddr": 12524002,
        "content": "00",
        "msgId": "123456"
    }
    try:
        response = requests.post(API_URL, json=data)
        if response.status_code == 200:
            logging.info(f"成功发送即时点火数据到 {API_URL}: {data}")
        else:
            logging.error(f"发送即时点火数据失败，状态码: {response.status_code}, 响应: {response.text}")
    except Exception as e:
        logging.error(f"即时点火请求失败: {e}")

# 查询烟炉状态逻辑
def handle_query_smoke_state():
    """
    处理查询烟炉状态指令，向 API 发送 JSON 数据
    """
    logging.info("处理查询烟炉状态指令...")
    data = {
        "groupName": "bdcivil",
        "portname": "NULL",
        "toAddr": 12524002,
        "content": "0f",
        "msgId": "123456"
    }
    try:
        response = requests.post(API_URL, json=data)
        if response.status_code == 200:
            logging.info(f"成功发送查询烟炉状态数据到 {API_URL}: {data}")
        else:
            logging.error(f"发送查询烟炉状态数据失败，状态码: {response.status_code}, 响应: {response.text}")
    except Exception as e:
        logging.error(f"查询烟炉状态请求失败: {e}")

# 启动心跳线程
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

    # 保持主线程运行
    while True:
        time.sleep(1)
