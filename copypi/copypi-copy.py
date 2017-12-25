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
import errno

parser = argparse.ArgumentParser(description='Main Process for copy handling')
parser.add_argument('--host',type=str,default='127.0.0.1',required=False,help='MQTT Server hostname or IP')
parser.add_argument('--port',type=str,default=1883,required=False,help='MQTT Server port')
args = parser.parse_args()

import traceback
def log(*args):
	mqttc.publish("log/copy",payload=" ".join([x for x in args]))

def error(e):
	estr = ''.join(sys.exc_info())
	trace = ''.join(traceback.format_stack())
	log("Error",estr,trace)

def mkdir_p(path):
	try: os.makedirs(path)
	except OSError as exc:
		if os.path.isdir(path): pass
		else: raise

class CopyThread(threading.Thread):
	def __init__(self, data):
		super(CopyThread, self).__init__()
		self.stoprequest = threading.Event()
		self.data = copy.deepcopy(data)
		self.id = data.get('id')
		self.hash = hashlib.sha1(data.get('mount_point').encode('utf-8')).hexdigest()
		self.target_dir = data.get('target_dir')
		self.mount_point = data.get('mount_point')
		self.copy = []
		self.last_msg = {}

	def run(self):
		while not self.stoprequest.isSet():
			try:
				id,src,dst = self.copy.pop(0)
				if os.path.exists(src):
					try:
						self.send_copy_msg(True)
						mkdir_p(os.path.dirname(dst))
						if not os.path.exists(dst) or os.stat(src).st_size != os.stat(dst).st_size:
							#print(self.id,"copying","->","true")
							shutil.copy2(src,dst)
							#print(self.id,":",src,"->",dst)
						#print(src,dst,len(self.copy))
					except OSError as err:
						print(err)
						if err.errno in [errno.EFBIG,errno.ENOSPC,errno.ENFILE,errno.EROFS,errno.ENODEV,errno.EBUSY]:
							self.send_error_msg(err)
						time.sleep(1)
					finally:
						#print(self.id,"copying","->","false")
						if len(self.copy) <= 0:
							self.send_copy_msg(False)
						#print(self.id,"files")
						self.send_files_msg()
			except IndexError as e:
				time.sleep(0.5)

	def send_files_msg(self):
		self.send_msg("copy/status/files/%s"%self.hash,json.dumps([x[1] for x in self.copy]))

	def send_copy_msg(self,status):
		self.send_msg("copy/status/copying/%s"%self.hash,'true' if status else 'false')

	def send_error_msg(self,err):
		if not err is None:
			self.send_msg("copy/status/error/%s"%self.hash,json.dumps({
				'error':True,
				'error_msg':str(err)
			}), retain=False)

	def send_msg(self,topic,payload,retain=True):
		if self.last_msg.get(topic,None) != payload:
			infot = mqttc.publish(topic, payload=payload, qos=1, retain=retain)
			if not infot is None:
				infot.wait_for_publish()
		self.last_msg[topic]=payload

	def mount(self,data):
		mount_point = data.get('mount_point')
		mtc = len(mount_point)+1
		files = data.get('files')
		local_target = os.path.join(self.target_dir,data.get('id'))
		for src_file in files:
			self.copy.append((data.get('id'),src_file,os.path.join(local_target,src_file[mtc:])))
		print(self.id,"files3")
		self.send_files_msg()
		print(self.id,"mount ->",data.get('mount_point'))

	def unmount(self,data):
		id = data.get('id')
		for i, v in reversed(list(enumerate(self.copy))):
			if id == v[0]:
				self.copy.pop(i)
		print(self.id,"files4")
		self.send_files_msg()
		print(self.id,"unmount ->",data.get('mount_point'))

	def join(self, timeout=None):
		self.stoprequest.set()
		super(CopyThread, self).join(timeout)

def msg_worker(msg_q):
	mounts = {}
	threads = {}
	while True:
		msg = msg_q.get()
		if msg.get('type') == 'mount':
			base_folder = msg.get('mount_point')
			print("mounted ->",base_folder,"->",msg.get("device_file"))
			statvfs = os.statvfs(base_folder)
			target_dir = os.path.join(os.path.join(base_folder,'shared'),time.strftime('%Y.%m.%d'))
			mounts[base_folder]={
				'files':[],
				'target_dir':target_dir,
				'id':os.path.basename(base_folder),
				'mount_point':base_folder,
				'device_file':msg.get('device_file'),
				'device_size':statvfs.f_frsize*statvfs.f_blocks,
				'device_free':statvfs.f_frsize*statvfs.f_bavail,
				'hub_port':msg.get('hub_port')
			}
			mkdir_p(target_dir)
			for root, directories, filenames in os.walk(base_folder):
				if root == base_folder: directories[:] = [d for d in directories if d not in ['shared']]
				for filename in filenames:
					abs_file = os.path.join(root,filename)
					mounts[base_folder]['files'].append(abs_file)
					#mounts[base_folder]['size']+=os.stat(abs_file).st_size
			thread = CopyThread(mounts[base_folder])
			threads[base_folder]=thread
			thread.start()
			for k,v in mounts.items():
				if k == base_folder: continue
				else: thread.mount(v)
			for k,v in threads.items():
				if k == base_folder: continue
				else: v.mount(mounts[base_folder])
		elif msg.get('type') == 'unmount':
			print("unmounted ->",msg.get('mount_point'),"->",msg.get("device_file"))
			mount = mounts.pop(msg.get('mount_point'), None)
			thread = threads.pop(msg.get('mount_point'), None)
			if not thread is None: thread.join(2.0)
			#if os.path.exists(msg.get('mount_point')): shutil.rmtree(msg.get('mount_point'),ignore_errors=True)
			if not mount is None:
				for k,v in mounts.items():
					thread = threads.get(k)
					if not thread is None:
						thread.unmount(mount)
				print("unmount ->",mount.get('id'),"hub:",mount.get('hub_port'))

msg_q = queue.Queue()
threading.Thread(target=msg_worker, args=(msg_q,)).start()

def on_message(mqttc, obj, msg):
	payload = json.loads(msg.payload.decode('utf-8'))
	msg_q.put(payload)

mqttc = client.Client(client_id="copy_subscriber", clean_session=False)
mqttc.on_message = on_message
mqttc.connect(args.host, args.port, 60)
mqttc.subscribe("udisks-glue", 1)
mqttc.loop_forever()
