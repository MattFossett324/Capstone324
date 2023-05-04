import serial
from time import sleep
import requests
import pygame
import RPi.GPIO as GPIO
import signal
from enum import Enum
import random

#Scanner Setup
ser = serial.Serial("/dev/serial0", 9600)
SCAN_CMD = b'\x7E\x00\x08\x01\x00\x02\x01\xAB\xCD'

#Web Setup
URL = 'https://capstonetestserver.logansinclair.me'

#Audio Setup
pygame.mixer.init()
soundSuccess = pygame.mixer.Sound('/home/pi/Scanner/success.wav')
soundFail1 = pygame.mixer.Sound('/home/pi/Scanner/fail1.wav')
soundFail2 = pygame.mixer.Sound('/home/pi/Scanner/fail2.wav')
soundFail3 = pygame.mixer.Sound('/home/pi/Scanner/fail3.wav')
soundFails = [soundFail1, soundFail2, soundFail3]

#LED Setup
GREEN_LED =  16
YELLOW_LED = 18
RED_LED = 22

GPIO.setmode(GPIO.BOARD)
GPIO.setup(GREEN_LED, GPIO.OUT)
GPIO.setup(YELLOW_LED, GPIO.OUT)
GPIO.setup(RED_LED, GPIO.OUT)

#Button Setup
BUTTON = 37
GPIO.setup(BUTTON, GPIO.IN, pull_up_down=GPIO.PUD_UP)

#Status Setup
class Status(Enum):
	READY = 1
	WAITING = 2
	ERROR = 3
	SUCC_SCAN = 4
	BAD_SCAN = 5
	BAD_NETWORK = 6

# UART Read
def read():
	recieved_data = ser.read()
	sleep(0.1)
	data_left = ser.inWaiting()
	recieved_data += ser.read(data_left)
	return recieved_data.decode("utf8")
# UART Write
def write(data):
	ser.write(data)
	return read()

#Process barcode data
def process(data):
	setStatus(Status.WAITING)
	strings = data.split(":")
	# Spiers Barcodes have 3 ":" in them
	if(len(strings) == 4):
		print("Battery Barcode: " + data)
		try:
			requests.post(URL, {"data": data}, timeout=5)
			setStatus(Status.SUCC_SCAN)
			soundSuccess.play()
		except requests.exceptions.RequestException as e:
			sound = random.choice(soundFails)
			sound.play()
			setStatus(Status.BAD_NETWORK)
		
	else:
		sound = random.choice(soundFails)
		sound.play()
		setStatus(Status.BAD_SCAN)
		print("Invalid Bacode: " + data)
		try:
			requests.post(URL, {"data": data}, timeout=5)
		except requests.exceptions.RequestException as e:
			pass

def turnOnRed():
	GPIO.output(GREEN_LED, GPIO.LOW)
	GPIO.output(YELLOW_LED, GPIO.LOW)
	GPIO.output(RED_LED, GPIO.HIGH)

def turnOnGreen():
	GPIO.output(GREEN_LED, GPIO.HIGH)
	GPIO.output(YELLOW_LED, GPIO.LOW)
	GPIO.output(RED_LED, GPIO.LOW)

def turnOnYellow():
	GPIO.output(GREEN_LED, GPIO.LOW)
	GPIO.output(YELLOW_LED, GPIO.HIGH)
	GPIO.output(RED_LED, GPIO.LOW)


def setStatus(status):
	if(status==Status.READY):
		turnOnGreen()
	elif(status==Status.WAITING):
		turnOnYellow()
	# Not Used
	elif(status==Status.ERROR):
		turnOnRed() 
	elif(status==Status.SUCC_SCAN):
		turnOnGreen()
		sleep(0.3)
		turnOnYellow()
		sleep(0.3)
		turnOnGreen()
		sleep(0.4)
	elif(status==Status.BAD_SCAN):
		turnOnRed()
		sleep(1)
	elif(status==Status.BAD_NETWORK):
		turnOnRed()
		sleep(0.3)
		turnOnYellow()
		sleep(0.3)
		turnOnRed()
		sleep(0.3)
		turnOnYellow()
		sleep(0.3)
		turnOnRed()
		sleep(0.3)

def signal_handler(sig, frame):
	print("Exiting...")
	GPIO.cleanup()
	sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

while True:
	setStatus(Status.WAITING)
	ser.write(SCAN_CMD)
	sleep(0.1)
	read() # clear response
	setStatus(Status.READY)
	data = read()
	process(data)