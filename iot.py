from machine import Pin, I2C
import utime
import neopixel
from TMG3993 import *
import network
import machine
import time
import ujson
from network import WLAN
import microcoapy
import coap_macros

#CoAP server key information
_SERVER_IP ='86.49.182.194'
_SERVER_PORT = 36105  #5683 36105 default CoAP port
_COAP_POST_URL = 'api/v1/IoT_07/telemetry' # fill your Device name, select based on your workstation
_COAP_GET_REQ_URL = 'api/v1/IoT_07/attributes' # fill your Device name, select based on your workstation
_COAP_AUT_PASS = 'authorization=IoT_07' # fill your Device name, select based on your workstation


i2c = I2C(0, scl=Pin(5), sda=Pin(4), freq=400000)
button = machine.Pin(22, machine.Pin.IN)
button_pressed = False
#classmachine.I2C(id, *, scl, sda, freq=400000, timeout=50000)


analog_value = machine.ADC(27)
np = neopixel.NeoPixel(machine.Pin(28), 1)
sensor = TMG3993(i2c)
sensor.enableEngines(0x01 | 0x02 | 0x10)


#Coap POST Message function.
def sendPostRequest(client, json):
    messageId = client.post(_SERVER_IP, _SERVER_PORT, _COAP_POST_URL, json,
                                   None, coap_macros.COAP_CONTENT_FORMAT.COAP_APPLICATION_JSON)
    print("[POST] Message Id: ", messageId)


#Coap PUT Message function.
def sendPutRequest(client):
    messageId = client.put(_SERVER_IP, _SERVER_PORT, "test",
                                   _COAP_AUT_PASS,
                                   coap_macros.COAP_CONTENT_FORMAT.COAP_TEXT_PLAIN)
    print("[PUT] Message Id: ", messageId)


#Coap GET Message function.
def sendGetRequest(client):
    messageId = client.get(_SERVER_IP, _SERVER_PORT, _COAP_GET_REQ_URL)
    print("[GET] Message Id: ", messageId)

#On message callback. Called each time when message that is not ACK is received.
def receivedMessageCallback(packet, sender):
    print('Message received:', packet.toString(), ', from: ', sender)
    print('Packet info received:', packet.messageid, ', from: ', sender)
    #print('hello world:', packet.messageid,
    
    #Process the message content here. TADA

#Creates JSON from the available peripherals
def createJSON():
    json_string={"Potentiometer":analog_value.read_u16(),"Lux":sensor.getLux(),"22":button.value()!=True}
    json = ujson.dumps(json_string)
    return json

#Connect to WiFi
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect("LPWAN-IoT-07", "LPWAN-IoT-07-WiFi")


#Create a CoAP client
client = microcoapy.Coap()
client.debug = True

#Set the callback function for the message reception
client.responseCallback = receivedMessageCallback

# Starting CoAP client
client.start()

#Time variables and period definition
ticks_start = time.ticks_ms()
get_ticks_start = time.ticks_ms()
get_period = 6500
send_period = 1500#ms

#Send get request to get the initial state of the LED
sendGetRequest(client)

#####################################################################################################################################################
def handle_interrupt(pin):
    # global variable/flag indicating press of precific button
    global button_pressed
    
    # check if pressed button is expected button
    if pin == button:
        # change state of flag to True/press detected
        button_pressed = True
    # handle wrong button press
    else:
        print("Not right button")
        print(pin)
button.irq(trigger=machine.Pin.IRQ_FALLING, handler = handle_interrupt)

def map_range(x, in_min, in_max, out_min, out_max):
    return int((x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min)
    
while True:
    reading = analog_value.read_u16()
    led_value = map_range(reading, 0, 65535, 0, 765)
    
    if(led_value <= 255):
        red_value = led_value
    else:
        red_value = 0
    if(led_value > 255 and led_value <= 510):
        green_value = led_value - 255
    else:
        green_value = 0
    if(led_value > 510):
        blue_value = led_value - 510
    else:
        blue_value = 0
        
       
    print("Potentiometer turn: ",reading)
   #print(led_value)
    np[0] = (red_value, green_value, blue_value) # set to red, full brightness
    print(red_value)
    print(green_value)
    print(blue_value)
    print(sensor.getLux())
    
    if button_pressed:
        print("Button is pressed")
        button_pressed = False
    
    np.write()
    utime.sleep(0.2)
    
        #If it is time to send data, create JSON and send it to the server
    if (time.ticks_diff(time.ticks_ms(), ticks_start) >= send_period):
        ticks_start=time.ticks_ms()
        json = createJSON()
        sendPostRequest(client, json)
      
    #Get the LED state from the server periodically
    #if (time.ticks_diff(time.ticks_ms(), get_ticks_start) >= get_period):
    #    get_ticks_start = time.ticks_ms()
    #    sendGetRequest(client)
    
    #Let the client do it's thing - send and receive CoAP messages.
    client.poll(10000, pollPeriodMs=1)
    
#Stop the client --- Should never get here.
client.stop()    
