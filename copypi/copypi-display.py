#!/usr/bin/python3
# -*- coding: utf-8 -*-
import json
import paho
import paho.mqtt.client as client
import argparse
import threading, queue

import epd2in13
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont
import time
from io import BytesIO
import base64

parser = argparse.ArgumentParser(description='Main Process for copy handling')
parser.add_argument('--host',type=str,default='127.0.0.1',required=False,help='MQTT Server hostname or IP')
parser.add_argument('--port',type=str,default=1883,required=False,help='MQTT Server port')
args = parser.parse_args()

PORT_CO = Image.open(BytesIO(base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAACAAAAAoCAQAAAA1IDASAAAAAmJLR0QA/4ePzL8AAAAJcEhZcwAACxMAAAsTAQCanBgAAAAHdElNRQfhDBkMKCnv2FgxAAAAHWlUWHRDb21tZW50AAAAAABDcmVhdGVkIHdpdGggR0lNUGQuZQcAAABwSURBVEjH7ZbBDsAgCEML2f//8exuuESZGV4kgRMeeFoKiUICgCAais3YBlzvA3+VyiESAgCuAG2SjdqnTew3iJMp7uPm4BPQ8o1yt4nWey4GXUdn1XHclSChVTLAXrm9l6m2sQAFKEABvG8Gs0t4AIZNE0wti6x0AAAAAElFTkSuQmCC')))
PORT_NC = Image.open(BytesIO(base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAACAAAAAoCAQAAAA1IDASAAAAAmJLR0QA/4ePzL8AAAAJcEhZcwAACxMAAAsTAQCanBgAAAAHdElNRQfhDBkNCQbJVBq8AAAAHWlUWHRDb21tZW50AAAAAABDcmVhdGVkIHdpdGggR0lNUGQuZQcAAADCSURBVEjHxVVRDsUgCGuJ979y97Vkc4p0i+/5YQwBUrAFSkgOAaQOiFX4eb9IkAcuE7CYKvDxRA0+vQQ0OrKnBBVtANDGZl1g50RqdbAcogk//P5uT7NK36oeAU0KdyXwhQr2UnnFAvkINHkbJWiIJkZGGT1o1yCawWYJY2VEVfeleaCJKxOas98L7Hqyai2fi4WAMVCi4qrkbyYjTWVWxJx3+rsaWZoOu3bjx9W2SUxWAhV5mPKgRqVwR5i1G/WLJh5yAC1QTF2EowAAAABJRU5ErkJggg==')))
PORT_AC = Image.open(BytesIO(base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAACAAAAAoCAQAAAA1IDASAAAAAmJLR0QAAKqNIzIAAAAJcEhZcwAACxMAAAsTAQCanBgAAAAHdElNRQfhDBkNAwGt32eVAAAAHWlUWHRDb21tZW50AAAAAABDcmVhdGVkIHdpdGggR0lNUGQuZQcAAAB5SURBVEjHY/z/n4EiwMTAMNQNYGRAC4P/BDWgqmIi114YYCFF+X8sTifOBX9wG8tEWQBSHAuMwyEh0c2A/7iSKJlJmZaZaQjHwn+S4OsmjDD4T2aJwIIvinAnCiqGAQspiYgmsTAaBiM5DH4eHDwFCsv/QVMiDZgBALX/MV0YcXaoAAAAAElFTkSuQmCC')))
PORT_ER = Image.open(BytesIO(base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAACAAAAAoCAQAAAA1IDASAAAAAmJLR0QA/4ePzL8AAAAJcEhZcwAACxMAAAsTAQCanBgAAAAHdElNRQfhDBkNCBAkm56sAAAAHWlUWHRDb21tZW50AAAAAABDcmVhdGVkIHdpdGggR0lNUGQuZQcAAADmSURBVEjH7VZBEoQgDEs6/v/L2QO6FikUdPcmBwe0DaGkGSnh0TDgBfALggCAuK6qYgIAfp8MILR/OSMvAEQ7u44oxqIkNhzUUD9WlOI91d29jrEeZabp5e3gGmeqAljv0hDWvD0CSzPxhoTkGehWugBsh2y0xEKFfgEoEy1A+FjWhsLps3e6UYvpgQ60lP4PQxlXgRlAXkT2ADStR1a12M7keSGxFpI3qxWI3WZ+0Ezjhs2a3bJ+z/zCZlSnO46kCYHrYKD07ApjnJDU7ff65ltOtnLiKMaimkfeROedfgu+vzjPAT4AilE/WzUePwAAAABJRU5ErkJggg==')))
PORT_BL = Image.new('1', (32,40), 255)

class Icon:
	def __init__(self,xy=(20,0),angle=None):
		self.xy = xy
		self.PORT_CO = PORT_CO if angle is None else PORT_CO.copy().rotate(angle=angle,expand=1)
		self.PORT_NC = PORT_NC if angle is None else PORT_NC.copy().rotate(angle=angle,expand=1)
		self.PORT_AC = PORT_AC if angle is None else PORT_AC.copy().rotate(angle=angle,expand=1)
		self.PORT_ER = PORT_ER if angle is None else PORT_ER.copy().rotate(angle=angle,expand=1)
		self.PORT_BL = PORT_BL if angle is None else PORT_BL.copy().rotate(angle=angle,expand=1)
		self.img = self.PORT_NC
		self._last_img = [None,None]

	def connected(self):
		self.img = self.PORT_CO # connected
		self._last_img = [None,None]

	def not_connected(self):
		self.img = self.PORT_NC # Not connected
		self._last_img = [None,None]

	def active(self):
		self.img = self.PORT_AC # Active (copy)
		self._last_img = [None,None]

	def error(self):
		self.img = self.PORT_ER # Active (copy)
		self._last_img = [None,None]

	def blank(self):
		self.img = self.PORT_BL # Blank
		self._last_img = [None,None]

	def render(self,epd,fidx):
		if self._last_img[fidx] != self.img:
			epd.set_frame_memory(self.img, self.xy[0], self.xy[1])
			self._last_img[fidx] = self.img

class SpeedIndicator:
	def __init__(self,xy=(20,0),angle=None):
		self.xy = xy
		self.angle = angle
		self.CLEAR = Image.new('1', (49,10), 255)
		if not self.angle is None:
			self.CLEAR = self.CLEAR.rotate(angle=self.angle,expand=1)
		self.BASE_IMG = Image.new('1', (49,10), 255)
		self.img = self.CLEAR
		self._last_speed = None
		self._last_img = [None,None]
		self.font = ImageFont.truetype('/usr/share/fonts/truetype/liberation2/LiberationSerif-Regular.ttf', 10)

	def sizeof_fmt(self,num, suffix='B'):
		for unit in ['','K','M','G','T','P','E','Z']:
			if abs(num) < 1024.0:
				return "%3.1f%s%s" % (num, unit, suffix)
			num /= 1024.0
		return "%.1f%s%s" % (num, 'Y', suffix)

	# bytes per second
	def speed(self,speed=None):
		if not speed is None and speed != self._last_speed:
				self.img = self.BASE_IMG.copy()
				draw = ImageDraw.Draw(self.img)
				msg = self.sizeof_fmt(speed)+"/s"
				#print(msg)
				draw.text((0,0),msg,font=self.font,fill=0)
				if not self.angle is None:
					self.img = self.img.rotate(angle=self.angle,expand=1)
				self._last_speed = speed
				self._last_img = [None,None]
		elif speed is None and speed != self._last_speed:
			self.blank()

	def blank(self):
		self.img = self.CLEAR
		self._last_speed = None
		self._last_img = [None,None]

	def render(self,epd,fidx):
		if self._last_img[fidx] is None:
			epd.set_frame_memory(self.img, self.xy[0], self.xy[1])
			self._last_img[fidx] = self.img


class FillIndicator:
	def __init__(self,xy=(20,0),angle=None):
		self.xy = xy
		self.angle = angle
		self.CLEAR = Image.new('1', (12,40), 255)
		if not self.angle is None:
			self.CLEAR = self.CLEAR.rotate(angle=self.angle,expand=1)
		self.BASE_IMG = Image.new('1', (12,40), 0)
		self._outline()
		self.img = self.CLEAR.copy()
		self._last_perc = [None,None]
		self._last_img = [None,None]

	def _outline(self):
		draw = ImageDraw.Draw(self.BASE_IMG)
		draw.rectangle(((1,1),(10,38)),fill=255)

	def fill(self,perc=0):
		if not perc is None and perc > -1 and perc <=100:
			perc = int(perc)
			if perc != self._last_perc:
				self.img = self.BASE_IMG.copy()
				w,h = self.img.size
				y1 = (h-2)-int(((h-4)/100)*perc)
				draw = ImageDraw.Draw(self.img)
				draw.rectangle(((2,y1),(9,37)),fill=0)
				if not self.angle is None:
					self.img = self.img.rotate(angle=self.angle,expand=1)
				self._last_perc = perc
				self._last_img = [None,None]
		else:
			self.blank()

	def blank(self):
		self.img = self.CLEAR
		self._last_perc = None
		self._last_img = [None,None]

	def render(self,epd,fidx):
		if self._last_img[fidx] != self.img:
			epd.set_frame_memory(self.img, self.xy[0], self.xy[1])
			self._last_img[fidx] = self.img

class Port:
	def __init__(self,xy=(20,5),angle=None):
		self.lock = threading.RLock()
		self.xy = xy
		self.angle = angle
		self.ic = Icon(self.xy,self.angle)
		if angle is None:
			self.fi = FillIndicator((xy[0]+37,xy[1]),self.angle)
			self.si = SpeedIndicator((xy[0],xy[1]+40),self.angle)
		else:
			self.fi = FillIndicator((xy[0],xy[1]+37),self.angle)
			self.si = SpeedIndicator((xy[0]-8,xy[1]),self.angle)

	def connected(self):
		with self.lock:
			self.ic.connected()
			self.si.speed(None)

	def not_connected(self):
		with self.lock:
			self.ic.not_connected()
			self.fi.fill(None)
			self.si.speed(None)

	def active(self):
		with self.lock:
			self.ic.active()

	def error(self):
		with self.lock:
			self.ic.error()

	def fill(self,perc=None):
		with self.lock:
			self.fi.fill(perc)

	def speed(self,speed=None):
		with self.lock:
			self.si.speed(speed)

	def render(self,epd,fidx):
		with self.lock:
			self.ic.render(epd,fidx)
			self.fi.render(epd,fidx)
			self.si.render(epd,fidx)

class DisplayThread(threading.Thread):
	def __init__(self):
		super(DisplayThread, self).__init__()
		self.epd = epd2in13.EPD()
		self.ports=[Port((80,184),-90),Port((80,107),-90),Port((80,27),-90),Port((10,5),None)]
		self.img_cls = Image.new('1', (epd2in13.EPD_WIDTH,epd2in13.EPD_HEIGHT), 255)
		self.init()
		self.last_dt = [None,None]
		self.date_image = None
		self.font = ImageFont.truetype('/usr/share/fonts/truetype/liberation2/LiberationSerif-Bold.ttf', 22)

	def init(self):
		self.epd.init(self.epd.lut_full_update)
		self.epd.set_frame_memory(self.img_cls, 0, 0)
		self.epd.display_frame()
		self.epd.init(self.epd.lut_partial_update)
		for i in range(2):
			self.epd.set_frame_memory(self.img_cls, 0, 0)

	def date_time(self,fidx):
		dt = time.strftime('%d.%m.%y')
		if self.last_dt[fidx] != dt:
			date_image = Image.new('1', (90, 20), 255)
			draw = ImageDraw.Draw(date_image)
			draw.text((0,0),dt,font=self.font,fill=0)
			self.date_image = date_image.rotate(angle=-90,expand=1)
			self.last_dt[fidx] = dt
			self.epd.set_frame_memory(self.date_image, 10, 65)
		time_image = Image.new('1', (90, 20), 255)
		tm = time.strftime('%H:%M:%S')
		draw = ImageDraw.Draw(time_image)
		draw.text((0,0),tm,font=self.font,fill=0)
		self.epd.set_frame_memory(time_image.rotate(angle=-90,expand=1), 10, 155)

	def get_port(self,num):
		if num > -1 and num < len(self.ports):
			return self.ports[num]
		return None

	def run(self):
		fidx = 0
		while True:
			start = time.time()
			for p in self.ports:
				p.render(self.epd,fidx)
			self.date_time(fidx)
			self.epd.display_frame()
			fidx = fidx + 1
			fidx %= 2
			wait = 2.0-(time.time()-start)
			if wait > 0.0: time.sleep(wait)

display_thread=DisplayThread()
display_thread.start()
msg_q = queue.Queue()
ps={}
def msg_worker(msg_q):
	while True:
		msg = msg_q.get()
		port_id = msg.get('port_id')
		port = display_thread.get_port(port_id)
		if port != None:
			#print(port_id,msg.get('copying',False),msg)
			if msg.get('copying',False):
				if msg.get('error',False):
					port.error()
				else:
					device_free = msg.get('device_free')
					if not ps.get(port_id,None) is None:
						free,tm = ps[port_id]
						sdf = free-device_free
						tdf = (time.time()-tm)
						port.speed(sdf/tdf)
					port.active()
					ps[port_id] = (device_free,time.time())
				port.fill(msg.get('device_used_percent',None))
			elif not msg.get('id',None) is None:
				if msg.get('error',False):
					port.error()
				else:
					port.connected()
				port.fill(msg.get('device_used_percent',None))
				port.speed(None)
				if not ps.get(port_id,None) is None: ps.pop(port_id,None)
			else:
				port.not_connected()
				port.speed(None)
				if not ps.get(port_id,None) is None: ps.pop(port_id,None)

threading.Thread(target=msg_worker, args=(msg_q,)).start()

def on_message(mqttc, obj, msg):
	port_id = (int(msg.topic.split('/')[-1])-1)
	payload = json.loads(msg.payload.decode('utf-8'))
	payload['port_id']=port_id
	msg_q.put(payload)

mqttc = client.Client(client_id="display_subscriber", clean_session=False)
mqttc.on_message = on_message
mqttc.connect(args.host, args.port, 60)
mqttc.subscribe("usb/ports/+", 1)
mqttc.loop_forever()
