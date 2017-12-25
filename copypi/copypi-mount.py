#!/usr/bin/python3
# -*- coding: utf-8 -*-

import argparse
import paho
import paho.mqtt.publish as publish
import json
import sys
import os
from os import listdir, readlink, chdir
from os.path import isfile, join, realpath, ismount
import stat

parser = argparse.ArgumentParser(description='Notify mqqt on mount/unmount of devices from udisks-glue')
parser.add_argument('--host',type=str,default='127.0.0.1',required=False,help='MQTT Server hostname or IP')
parser.add_argument('--port',type=str,default=1883,required=False,help='MQTT Server port')
parser.add_argument('-d','--device',type=str,required=True,help='full device patrh being (un)mounted eg: /dev/sda1')
parser.add_argument('-m','--mount',type=str,required=True,help='full mount path of device bein (un)mounted eg: /media/123-123')
parser.add_argument('-t','--type',type=str,required=True,choices=['mount','unmount'],help='action type')
args = parser.parse_args()

def disk_exists(path):
	try:return stat.S_ISBLK(os.stat(path).st_mode)
	except:return False

def mount_exists(path):
	return ismount(path)

def find_bus_id(device_name):
	try:
		DEVICE_PATH = "/dev/disk/by-path/"
		chdir(DEVICE_PATH)
		devices = [join(DEVICE_PATH, f) for f in listdir(DEVICE_PATH)]
		for device in devices:
			if "usb-usb" in device:
				target = realpath(readlink(device))
				if device_name == target:
					return int(device.split(":")[1].split(".")[1])
	except Exception as ex:
		print(ex)
	return None



if args.type == 'mount':
	if not disk_exists(args.device):
		print("%s does not exist!"%args.device)
		exit(2)
	if not mount_exists(args.mount):
		print("%s does not exist!"%args.mount)
		exit(2)

msg = {
  'type':args.type,
  'device_file':args.device,
  'mount_point':args.mount,
  'hub_port':find_bus_id(args.device) if disk_exists(args.device) else -1
}

publish.single('udisks-glue', payload=json.dumps(msg), qos=1, hostname=args.host, port=args.port)
