# coding=utf-8
import pymysql.cursors
import requests
import random
import time


def haha(log):
	url = "http://127.0.0.1:8000/test/?"
	p = []
	for k in log.keys():
		p.append("{}={}".format(k,log[k])) 
	requests.get(url=url+"&".join(p))

db = pymysql.connect("47.100.97.152","root","123456","AirConditioner" )
cursor = db.cursor()
cursor.execute("delete from Logger_runlog;")
db.commit()

print("hello")

import pandas as pd
data = pd.read_csv("data.csv",sep='\t',encoding='gb2312').values
maps = {'roomid':0,'temperature':1,'windspeed':2,'status':3,'logtype':4,'flag':5}
for row in data:
	log = {}
	for one in maps.keys():
		log[one] = row[maps[one]]
	if log['flag'] != "request_off":
		t = random.randint(10,20)
		print(t)
		time.sleep(t)
	haha(log)

