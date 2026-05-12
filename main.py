from yolobit import *
button_a.on_pressed = None
button_b.on_pressed = None
button_a.on_pressed_ab = button_b.on_pressed_ab = -1
from aiot_lcd1602 import LCD1602
import time
from mqtt import *
from machine import RTC, Pin, SoftI2C
import ntptime
from aiot_hcsr04 import HCSR04
from aiot_rgbled import RGBLed
from event_manager import *
from aiot_dht20 import DHT20

# --- GLOBAL STATE VARIABLES ---
fan_control = '0'
fan_mode = '0'
fan_speed = '0'
led_control = '0'
dor_ctrl = '0'
isDetectedYet = 0
temp = 0
humid = 0
light = 0

# --- HARDWARE INITIALIZATION ---
aiot_lcd1602 = LCD1602()
tiny_rgb = RGBLed(pin2.pin, 4)
aiot_dht20 = DHT20()
event_manager.reset()

# --- HARDWARE CONTROL LOGIC ---

def update_fan_state():
  """Calculates and applies the correct fan speed based on all current states."""
  # If fan is turned off globally
  if fan_control == '0':
    pin10.write_analog(0)
    return

  speed_percent = 0
  
  # AUTO MODE: Speed depends on temperature
  if fan_mode == '0':
    if temp >= 30:
      speed_percent = 100
    elif 25 <= temp < 30:
      speed_percent = 67
    elif 20 <= temp < 25:
      speed_percent = 33
    else:
      speed_percent = 0
      
  # MANUAL MODE: Speed depends on Adafruit slider/buttons
  elif fan_mode == '1':
    if fan_speed == '0':
      speed_percent = 33
    elif fan_speed == '1':
      speed_percent = 67
    elif fan_speed == '2':
      speed_percent = 100

  # Apply calculated speed
  pin10.write_analog(round(translate(speed_percent, 0, 100, 0, 1023)))

def humanSensorControl():
  global isDetectedYet
  
  if button_a.is_pressed():
    if isDetectedYet == 0:
      isDetectedYet = 1
      print("36")
    else:
      isDetectedYet = 0
    time.sleep_ms(300) # Debounce delay

def humanSensor():
  global light, led_control
  light = round(translate((pin1.read_analog()), 0, 4095, 0, 100))
  
  if light <= 20 and isDetectedYet == 0:
    print("18")
    if pin0.read_digital() == 1:
      tiny_rgb.show(0, hex_to_rgb('#ffffff'))
      led_control = '1'
      mqtt.publish('led-control', '1')

def tempHumidUpdate():
  global temp, humid
  aiot_dht20.read_dht20()
  temp = aiot_dht20.dht20_temperature()
  humid = aiot_dht20.dht20_humidity()
  
  mqtt.publish('temp', temp)
  mqtt.publish('humid', humid)
  
  # Temperature changed, which might affect the fan if it's in Auto Mode
  update_fan_state()

def overallDisplay():
  # T: XX*C H: XX%
  aiot_lcd1602.move_to(0, 0)
  aiot_lcd1602.putstr(f"T:{temp}*C H:{humid}%")
  
  # DD/MM/YY  HH:MM (2 spaces between date and time)
  dt = RTC().datetime()
  date_str = "%02d/%02d/%02d" % (dt[2], dt[1], dt[0] % 100) # Only show last 2 digits of year
  time_str = "%02d:%02d" % (dt[4], dt[5])
  
  aiot_lcd1602.move_to(0, 1)
  aiot_lcd1602.putstr(f"{date_str}  {time_str}")

# --- TIMERS ---

def timer_10s_callback():
  tempHumidUpdate()

def timer_1s_callback():
  overallDisplay()
  humanSensor()
  humanSensorControl()

event_manager.add_timer_event(10000, timer_10s_callback)
event_manager.add_timer_event(1000, timer_1s_callback)

# --- MQTT CALLBACKS ---

def on_mqtt_receive_fan_control(msg):
  global fan_control
  fan_control = msg
  update_fan_state()

def on_mqtt_receive_fan_mode(msg):
  global fan_mode
  fan_mode = msg
  update_fan_state()

def on_mqtt_receive_fan_speed(msg):
  global fan_speed
  fan_speed = msg
  update_fan_state()

def on_mqtt_receive_led_control(msg):
  global led_control
  led_control = msg
  if led_control == '1':
    tiny_rgb.show(0, hex_to_rgb('#ffffff'))
  else:
    tiny_rgb.show(0, hex_to_rgb('#000000'))

def on_mqtt_receive_door_control(msg):
  global dor_ctrl
  dor_ctrl = msg
  if dor_ctrl == '1':
    print(108)
    pin0.servo_write(90)
  else:
    pin0.servo_write(0)

def registerAda():
  mqtt.on_receive_message('fan-control', on_mqtt_receive_fan_control)
  mqtt.on_receive_message('fan-mode', on_mqtt_receive_fan_mode)
  mqtt.on_receive_message('fan-speed', on_mqtt_receive_fan_speed)
  mqtt.on_receive_message('led-control', on_mqtt_receive_led_control)
  mqtt.on_receive_message('door-control', on_mqtt_receive_door_control)

# --- SETUP AND MAIN LOOP ---

if True:
  display.show(Image("20002:02020:00200:00200:00200"))
  aiot_lcd1602.move_to(0, 0)
  aiot_lcd1602.putstr('Yolo Home')
  time.sleep_ms(1000)
  aiot_lcd1602.clear()
  
  mqtt.connect_wifi('HCMUT03', 'nguyen1612')
  mqtt.connect_broker(server='io.adafruit.com', port=1883, username='kh01nguy3n', password='aio_vjkl99p8mm56BabV1PcI9KYMliHl')
  registerAda()
  
  fan_speed = '0'
  fan_control = '0'
  fan_mode = '0'
  led_control = '0'
  dor_ctrl = '0'
  isDetectedYet = 0
  
  ntptime.host = "time.google.com"
  ntptime.settime()
  (year, month, mday, week_of_year, hour, minute, second, milisecond) = RTC().datetime()
  RTC().init((year, month, mday, week_of_year, hour+7, minute, second, milisecond))
  
  aiot_ultrasonic = HCSR04(trigger_pin=pin3.pin, echo_pin=pin6.pin)
  tiny_rgb.show(0, hex_to_rgb('#000000'))
  
  aiot_lcd1602.clear()
  aiot_lcd1602.move_to(0, 0)
  aiot_lcd1602.putstr('Connected')
  time.sleep_ms(1000)
  aiot_lcd1602.clear()

while True:
  if mqtt.wifi_connected():
    print(f"67", end=' ')
    
  mqtt.check_message()
  event_manager.run()
  time.sleep_ms(1000)