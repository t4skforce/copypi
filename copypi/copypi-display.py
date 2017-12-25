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

	def connected(self):
		self.img = self.PORT_CO # connected

	def not_connected(self):
		self.img = self.PORT_NC # Not connected

	def active(self):
		self.img = self.PORT_AC # Active (copy)

	def error(self):
		self.img = self.PORT_ER # Active (copy)

	def blank(self):
		self.img = self.PORT_BL # Blank

	def render(self,img):
		img.paste(self.img,self.xy)

class FillIndicator:
	def __init__(self,xy=(20,0),angle=None):
		self.xy = xy
		self.angle = angle
		self.CLEAR = Image.new('1', (12,40), 255)
		self.BASE_IMG = Image.new('1', (12,40), 0)
		self._outline()
		self.img = self.CLEAR.copy()
		self._last_perc = None

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
				self._last_perc = perc
		else:
			self.img = self.CLEAR
			self._last_perc = None

	def blank(self):
		self.img = self.CLEAR

	def render(self,img):
		if not self.angle is None: img.paste(self.img.rotate(angle=self.angle,expand=1),self.xy)
		else: img.paste(self.img,self.xy)

class Port:
	def __init__(self,xy=(20,5),angle=None):
		self.xy = xy
		self.angle = angle
		self.ic = Icon(self.xy,self.angle)
		if angle is None: self.fi = FillIndicator((xy[0]+37,xy[1]),self.angle)
		else: self.fi = FillIndicator((xy[0],xy[1]+37),self.angle)

	def connected(self):
		self.ic.connected()

	def not_connected(self):
		self.ic.not_connected()
		self.fi.fill(None)

	def active(self):
		self.ic.active()

	def error(self):
		self.ic.error()

	def fill(self,perc=None):
		self.fi.fill(perc)

	def render(self,img):
		self.ic.render(img)
		self.fi.render(img)

class DisplayThread(threading.Thread):
	def __init__(self):
		super(DisplayThread, self).__init__()
		self.ports=[Port((80,184),-90),Port((80,107),-90),Port((80,27),-90),Port((10,5),None)]
		self.epd = epd2in13.EPD()
		self.img_cls = Image.new('1', (epd2in13.EPD_WIDTH,epd2in13.EPD_HEIGHT), 255)
		self.init()

	def init(self):
		self.epd.init(self.epd.lut_full_update)
		self.epd.set_frame_memory(self.img_cls, 0, 0)
		self.epd.display_frame()
		self.epd.init(self.epd.lut_partial_update)

	def date_time(self,img):
		time_image = Image.new('1', (180, 20), 255)
		image_width, image_height  = time_image.size
		draw = ImageDraw.Draw(time_image)
		font = ImageFont.truetype('/usr/share/fonts/truetype/liberation2/LiberationSerif-Bold.ttf', 22)
		msg = time.strftime('%d.%m.%y %H:%M:%S')
		mw, mh = draw.textsize(msg, font = font)
		draw.text((0,(image_height-mh)-2), msg, font = font, fill = 0)
		img.paste(time_image.rotate(angle=-90,expand=1),(5,65))

	def get_port(self,num):
		if num > -1 and num < len(self.ports):
			return self.ports[num]
		return None

	def run(self):
		while True:
			img = Image.new('1', (epd2in13.EPD_WIDTH,epd2in13.EPD_HEIGHT), 255)
			for p in self.ports: p.render(img)
			self.date_time(img)
			self.epd.set_frame_memory(img, 0, 0)
			self.epd.display_frame()
			time.sleep(0.1)

display_thread=DisplayThread()
display_thread.start()
msg_q = queue.Queue()
def msg_worker(msg_q):
	while True:
		msg = msg_q.get()
		port = display_thread.get_port(msg.get('port_id'))
		if port != None:
			if msg.get('copying',False):
				if msg.get('error',False): port.error()
				else: port.active()
				port.fill(msg.get('device_used_percent',None))
			elif not msg.get('id',None) is None:
				if msg.get('error',False): port.error()
				else: port.connected()
				port.fill(msg.get('device_used_percent',None))
			else:
				port.not_connected()

threading.Thread(target=msg_worker, args=(msg_q,)).start()

def on_message(mqttc, obj, msg):
	port_id = (int(msg.topic.split('/')[-1])-1)
	payload = json.loads(msg.payload.decode('utf-8'))
	payload['port_id']=port_id
	msg_q.put(payload)

mqttc = client.Client(client_id="display_subscriber",clean_session=False)
mqttc.on_message = on_message
mqttc.connect(args.host, args.port, 60)
mqttc.subscribe("usb/ports/+", 1)
mqttc.loop_forever()
