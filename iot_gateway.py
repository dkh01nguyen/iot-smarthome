import serial.tools.list_ports
import time
import sys
import json
from Adafruit_IO import MQTTClient

# ================= CREDENTIALS =================
AIO_USERNAME = "kh01nguy3n"
AIO_KEY = "aio_vjkl99p8mm56BabV1PcI9KYMliHl"


# AIO_FEED_SINGLE = "led-control-control"
AIO_FEED_LIST = ["control", "home-data"]
# ================================================================

serial_buffer = ""

sensor_state = {
    "temp": 0.0, 
    "humid": 0.0,
    "electricity": 0.0
}

# ================= MQTT =================
def connected(client):
    print("[MQTT] Kết nối thành công tới Adafruit IO!") 
    # 1 Feed subscription
    # client.subscribe(AIO_FEED_LIST)
    
    # Multiple Feeds subscription
    for feed in AIO_FEED_LIST:
        client.subscribe(feed)

def subscribe(client, userdata, mid, granted_qos):
    print(f"[MQTT] Đã subscribe thành công!")

def disconnected(client):
    print("[MQTT] Ngắt kết nối...")
    sys.exit(1)

def message(client, feed_id, payload):
    """
    Server -> string -> hardware
    """
    print(f"\n[MQTT Nhận] Feed: {feed_id} | Dữ liệu: {payload}")
    try:
        control_data = json.loads(payload)
        
        if "led-control" in control_data:
            val = str(control_data["led-control"]).strip().upper()
            cmd = "LED_CTRL=ON" if val in ["1", "ON", "TRUE"] else "LED_CTRL=OFF"
            ser.write(cmd.encode("UTF-8"))
            print(f"[Serial Gửi] {cmd}")

        
        if "door-control" in control_data:
            val = str(control_data["door-control"]).strip().upper()
            cmd = "DOR_CTRL=UNLOCK" if val in ["1", "UNLOCK", "OPEN", "TRUE"] else "DOR_CTRL=LOCK"
            ser.write(cmd.encode("UTF-8"))
            print(f"[Serial Gửi] {cmd}")

        
        if "fan-control" in control_data:
            val = str(control_data["fan-control"]).strip().upper()
            cmd = "FAN_CTRL=ON" if val in ["1", "ON", "TRUE"] else "FAN_CTRL=OFF"
            ser.write(cmd.encode("UTF-8"))
            print(f"[Serial Gửi] {cmd}")

        
        if "fan-mode" in control_data:
            val = str(control_data["fan-mode"]).strip().upper()
            cmd = f"FAN_MODE=AUTO" if val in ["1", "AUTO"] else "FAN_MODE=MANUAL"
            ser.write(cmd.encode("UTF-8"))
            print(f"[Serial Gửi] {cmd}")

        if "fan-speed" in control_data:
            val = str(control_data["fan-speed"]).strip().upper()
            if val in ["LOW", "0"]: cmd = "FAN_SPED=LOW"
            elif val in ["MED", "MEDIUM", "1"]: cmd = "FAN_SPED=MED"
            elif val in ["HIGH", "2"]: cmd = "FAN_SPED=HIGH"
            else: cmd = None
            
            if cmd:
                ser.write(cmd.encode("UTF-8"))
                print(f"[Serial Gửi] {cmd}")

    except json.JSONDecodeError:
        print("[Lỗi] Payload từ server không phải định dạng JSON.")

# ================= SERIAL =================
def getPort():
    ports = serial.tools.list_ports.comports()
    for port in ports:
        strPort = str(port)
        if "USB Serial Device" in strPort or "CH340" in strPort or "CP210" in strPort:
            return strPort.split(" ")[0]
    return "None"

# def process_raw_string(raw_data):
#     """
#     Cách 1: Xử lý chuỗi thô (VD: !TEMP:32.5#). Gom vào JSON chung và gửi lên server.
#     """
#     global sensor_state
#     print(f"[Serial Nhận - Chuỗi thô] {raw_data}")
    
#     # Bỏ dấu ! và #, sau đó tách ra bởi dấu :
#     clean_data = raw_data.replace("!", "").replace("#", "")
#     parts = clean_data.split(":")
    
#     if len(parts) == 2:
#         field = parts[0]
#         try:
#             value = float(parts[1]) if '.' in parts[1] else int(parts[1])
            
#             # Cập nhật dictionary
#             if field == "TEMP":
#                 sensor_state["temp"] = value
#             elif field == "HUMID":
#                 sensor_state["humid"] = value
#             elif field == "ELECTRICITY":
#                 sensor_state["electricity"] = value
#             # Publish 1 Feed duy nhất chứa toàn bộ JSON
#             client.publish(AIO_FEED_LIST[1], json.dumps(sensor_state))
            
#             # Nếu dùng nhiều Feed sau này:
#             # if field == "TEMP": client.publish("temp-feed", value)
            
#         except ValueError:
#             pass

def process_direct_json(json_data):
    print(f"[Serial Nhận - JSON trực tiếp] {json_data}")
    try:
        # Validate 
        parsed_json = json.loads(json_data)

        client.publish(AIO_FEED_LIST[1], json.dumps(parsed_json))
    except json.JSONDecodeError:
        print("[Lỗi] Phần cứng gửi lên chuỗi lỗi, không parse được JSON.")

def readSerial():
    global serial_buffer
    bytesToRead = ser.inWaiting()
    if bytesToRead > 0:
        serial_buffer += ser.read(bytesToRead).decode("UTF-8")
        
        while " " in serial_buffer:
            end_idx = serial_buffer.find(" ")
            packet = serial_buffer[:end_idx].strip()
            
            if packet:
                # if packet.startswith("!") and packet.endswith("#"):
                #     process_raw_string(packet)
                if packet.startswith("{") and packet.endswith("}"):
                    process_direct_json(packet)
            
            # Xóa
            serial_buffer = serial_buffer[end_idx + 1:]

# ================= GATEWAY =================
port_name = getPort()
if port_name != "None":
    print(f"[Hệ thống] Mở cổng Serial tại {port_name}...")
    ser = serial.Serial(port=port_name, baudrate=115200)
else:
    print("[Lỗi] Không tìm thấy mạch phần cứng!")
    sys.exit(1)

# Adafruit MQTT
client = MQTTClient(AIO_USERNAME, AIO_KEY)
client.on_connect = connected
client.on_disconnect = disconnected
client.on_message = message
client.on_subscribe = subscribe

client.connect()
# Background MQTT
client.loop_background()

try:
    print("[Hệ thống] Gateway Full-Duplex đang chạy...")
    while True:
        readSerial()
        time.sleep(1) # Tránh treo CPU
except KeyboardInterrupt:
    print("\n[Hệ thống] Đang ngắt kết nối...")
    client.disconnect()
    ser.close()
    sys.exit(0)