import socket
import binascii

def calculate_bcc(data):
    """
    计算BCC校验码
    :param data: 字符串形式的报文
    :return: 计算出的校验位
    """
    bcc = 0
    for byte in data:
        bcc ^= ord(byte)
    return f"{bcc:02X}"


def process_hex_data(received_hex):
    """
    处理接收到的 HEX 数据，插入所需烟炉数据并调整长度和校验位
    :param received_hex: 接收到的 HEX 数据
    :return: 修改后的报文
    """
    # 转换 HEX 数据为 ASCII
    received_ascii = binascii.unhexlify(received_hex.replace(" ", "")).decode("ascii")
    print(f"原始ASCII: {received_ascii}")

    # 分析并提取字段
    header = received_ascii[:8]  # $#0001TB
    data_length = int(received_ascii[8:11])  # 数据长度
    main_content = received_ascii[11:-2]  # 数据段
    checksum = received_ascii[-2:]  # 校验位

    print(f"原始字段 - 头部: {header}, 数据长度: {data_length}, 主体内容: {main_content}, 校验: {checksum}")

    # 分割内容
    time_field = main_content[:12]  # 时间字段
    smoke_group_1 = main_content[12:40]  # 第一组烟炉状态
    smoke_group_3 = main_content[40:68]  # 第三组烟炉状态
    remaining_data = main_content[68:]  # 后续字段

    print(f"时间: {time_field}, 第一组烟炉状态: {smoke_group_1}, 第三组烟炉状态: {smoke_group_3}, 后续字段: {remaining_data}")

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
    print(f"最终报文: {final_report}")

    return final_report


def send_udp_report(final_report, ip_address, port):
    """
    将最终报文转换为 HEX 并通过 UDP 协议发送
    :param final_report: 最终 ASCII 报文
    :param ip_address: 目标 IP 地址
    :param port: 目标端口
    """
    try:
        # 转换 ASCII 报文为 HEX 字节流
        hex_report = binascii.hexlify(final_report.encode('ascii')).decode('ascii')

        # 在最前面追加固定 HEX 数据
        fixed_prefix = "7B8100103131313131313131313131317B"
        complete_hex_report = fixed_prefix + hex_report

        # 创建 UDP 套接字
        udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # 发送 HEX 数据到目标地址
        udp_socket.sendto(binascii.unhexlify(complete_hex_report), (ip_address, port))

        print(f"成功发送报文到 {ip_address}:{port}")
        print(f"发送的完整 HEX 数据: {complete_hex_report}")
    except Exception as e:
        print(f"发送报文失败: {e}")
    finally:
        udp_socket.close()


# 示例接收到的 HEX 数据
received_hex = "24 23 30 30 30 31 54 42 30 38 38 32 34 31 32 32 33 31 35 30 37 34 37 31 35 35 35 35 35 35 35 35 35 35 35 35 35 35 35 35 35 35 35 35 35 35 35 35 35 35 35 35 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 31 32 36 31 30 30 30 30 30 30 30 30 30 30 30 30 30 30 30 57 34 37"

# 处理并生成修改后的报文
final_data = process_hex_data(received_hex)

# 目标 IP 和端口
target_ip = "182.92.85.227"
target_port = 7000

# 调用发送函数
send_udp_report(final_data, target_ip, target_port)
