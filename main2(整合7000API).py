import socket
import binascii
import logging
from flask import Flask, request, jsonify

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)

# BCC校验计算
def calculate_bcc(data):
    """
    计算BCC校验码
    """
    bcc = 0
    for byte in data:
        bcc ^= ord(byte)
    return f"{bcc:02X}"


# 处理接收到的 content 字段
def process_content(content):
    """
    解析 content 字段，生成并返回需要转发的最终报文
    """
    # 解析 HEX 数据为 ASCII
    received_ascii = binascii.unhexlify(content).decode("ascii")
    logging.info(f"接收到的ASCII数据: {received_ascii}")

    # 分析并提取字段
    header = received_ascii[:8]  # $#0001TB
    data_length = int(received_ascii[8:11])  # 数据长度
    main_content = received_ascii[11:-2]  # 数据段
    checksum = received_ascii[-2:]  # 校验位

    # logging.info(f"原始字段 - 头部: {header}, 数据长度: {data_length}, 主体内容: {main_content}, 校验: {checksum}")

    # 分割内容
    time_field = main_content[:12]  # 时间字段
    smoke_group_1 = main_content[12:40]  # 第一组烟炉状态
    smoke_group_3 = main_content[40:68]  # 第三组烟炉状态
    remaining_data = main_content[68:]  # 后续字段

    # logging.info(f"时间: {time_field}, 第一组烟炉状态: {smoke_group_1}, 第三组烟炉状态: {smoke_group_3}, 后续字段: {remaining_data}")

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
    fixed_prefix = "7B0900103131313131313131313131317B"
    final_hex_report = fixed_prefix + binascii.hexlify(final_report.encode("ascii")).decode("ascii")
    return final_hex_report


def forward_to_udp_server(final_hex_report, ip_address="182.92.85.227", port=5023):
    """
    将 HEX 格式数据通过 UDP 协议发送并接收回复
    """
    try:
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_socket.settimeout(10)  # 设置超时时间为 5 秒
        udp_socket.sendto(binascii.unhexlify(final_hex_report), (ip_address, port))
        #udp_socket.sendto(binascii.unhexlify("7B01001631313131313131313131310000000000007B"), (ip_address, port))
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
@app.route('/api/data/rv', methods=['POST'])
def receive_data():
    data = request.json
    logging.info(f"接收到的数据: {data}")

    if 'commInfos' in data:
        for item in data['commInfos']:
            content = item.get('content')  # 获取 HEX 数据
            if content:
                try:
                    # 去除空格
                    cleaned_content = content.replace(" ", "")

                    # 将 HEX 转换为 ASCII
                    ascii_data = binascii.unhexlify(cleaned_content).decode('ascii')
                    # logging.info(f"转换后的 ASCII 数据: {ascii_data}")

                    # 处理数据并生成最终报文
                    final_hex_report = process_content(cleaned_content)
                    logging.info(f"最终需转发的 HEX 数据: {final_hex_report}")

                    # 转发数据
                    forward_to_udp_server(final_hex_report)

                except (binascii.Error, UnicodeDecodeError) as e:
                    logging.error(f"处理数据失败: {e}")
                    return jsonify({"status": "error", "message": "Invalid HEX data"}), 400
    return jsonify({"status": "200"}), 200


if __name__ == '__main__':
    app.run(debug=False, host="0.0.0.0", port=7000, threaded=True)
