#!/usr/bin/python3
# -*- coding: utf-8 -*-
import os
import time
import json
import copy
import shutil
import paho
import paho.mqtt.client as client
import argparse
import threading, queue
import hashlib

parser = argparse.ArgumentParser(description='Main Process for copy handling')
parser.add_argument('--host',type=str,default='127.0.0.1',required=False,help='MQTT Server hostname or IP')
parser.add_argument('--port',type=str,default=1883,required=False,help='MQTT Server port')
args = parser.parse_args()


class PortStatusThread(threading.Thread):
	def __init__(self, data):
		super(PortStatusThread, self).__init__()
		self.stoprequest = threading.Event()
		self.iscopying = threading.Event()
		self.id = data.get('id')
		self.hash = hashlib.sha1(data.get('mount_point').encode('utf-8')).hexdigest()
		self.hub_port = data.get('hub_port')
		self.mount_point = data.get('mount_point')
		self.device_file = data.get('device_file')
		self.last_msg = None
		self.files = []
		self.hash = hashlib.sha1(self.id.encode('utf-8')).hexdigest()
		self.error = False
		self.error_msg = ""

	def set_files(self, files):
		self.files = files

	def set_error(self, msg):
		self.error = True
		self.error_msg = msg

	def copy(self, status=False):
		if status:
			self.iscopying.set()
		else:
			self.iscopying.clear()

	def run(self):
		while not self.stoprequest.isSet():
			self.notify()
			time.sleep(1)

	def notify(self):
		if not self.stoprequest.isSet() and os.path.exists(self.mount_point):
			fcnt = len(self.files)
			if self.iscopying.is_set(): fcnt+=1
			statvfs = os.statvfs(self.mount_point)
			device_size=statvfs.f_frsize*statvfs.f_blocks
			device_free=statvfs.f_frsize*statvfs.f_bavail
			self.publish(self.id,self.iscopying.is_set(),fcnt,device_size,device_free)
		elif not self.stoprequest.isSet():
			self.publish()

	def publish(self, id=None, copying=False, files_left=0, device_size=None, device_free=None):
		msg = json.dumps({
			'id':id,
			'copying':copying,
			'files_left':files_left,
			'error':self.error,
			'error_msg':self.error_msg,
			'device_used_percent':int((device_size-device_free)/(device_size/100.0)) if not device_size is None and not device_free is None else None,
			'device_size':device_size,
			'device_free':device_free,
			'device_used':device_size-device_free if not device_size is None and not device_free is None else None
		})
		if self.last_msg != msg:
			#print("sending","usb/ports/%d"%self.hub_port,"->",msg)
			infot = mqttc.publish("usb/ports/%d"%self.hub_port,payload=msg,qos=1,retain=True)
			if not infot is None:
				infot.wait_for_publish()
			#print("ok","usb/ports/%d"%self.hub_port,"->",msg)
		self.last_msg = msg

	def join(self, timeout=None):
		self.stoprequest.set()
		self.publish()
		super(PortStatusThread, self).join(timeout)

mounts = {}
threads = {}

def msg_worker(msg_q):
	while True:
		msg = msg_q.get()
		if msg.get('type') == 'mount':
			base_folder = msg.get('mount_point')
			print("mounted ->",base_folder,"->",msg.get("device_file"))
			hash = hashlib.sha1(msg.get('mount_point').encode('utf-8')).hexdigest()
			mounts[hash]={
				'id':os.path.basename(base_folder),
				'hash': hash,
				'mount_point':base_folder,
				'device_file':msg.get('device_file'),
				'hub_port':msg.get('hub_port')
			}
			thread = PortStatusThread(mounts[hash])
			threads[hash]=thread
			thread.start()
		elif msg.get('type') == 'unmount':
			base_folder = msg.get('mount_point')
			print("unmounted ->",msg.get('mount_point'),"->",msg.get("device_file"))
			hash = hashlib.sha1(base_folder.encode('utf-8')).hexdigest()
			mount = mounts.pop(hash, None)
			thread = threads.pop(hash, None)
			if not thread is None:
				thread.join(2.0)

msg_q = queue.Queue()
threading.Thread(target=msg_worker, args=(msg_q,)).start()

def set_files(mosq, obj, msg):
	hash = msg.topic.split('/')[-1]
	thread = threads.get(hash,None)
	if not thread is None:
		thread.set_files(json.loads(msg.payload.decode('utf-8')))

def is_copying(mosq, obj, msg):
	hash = msg.topic.split('/')[-1]
	thread = threads.get(hash,None)
	if not thread is None:
		status = msg.payload.decode('utf-8').lower() in ['true','yes','1']
		thread.copy(status)

def set_error(mosq, obj, msg):
	hash = msg.topic.split('/')[-1]
	thread = threads.get(hash,None)
	if not thread is None:
		thread.set_error(msg.payload.decode('utf-8'))

def on_message(mqttc, obj, msg):
	payload = json.loads(msg.payload.decode('utf-8'))
	msg_q.put(payload)

mqttc = client.Client(client_id="status_subscriber", clean_session=True)
mqttc.message_callback_add("copy/status/files/#", set_files)
mqttc.message_callback_add("copy/status/copying/#", is_copying)
mqttc.on_message = on_message
mqttc.connect(args.host, args.port, 60)
mqttc.subscribe([("udisks-glue", 1),("copy/status/files/#",1),("copy/status/copying/#",1)])
mqttc.loop_forever()
