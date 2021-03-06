from django.apps import AppConfig
from django.db.models import Q
from django.http import Http404
from django.utils.dateparse import parse_date
from Logger import models
from django.shortcuts import render
import datetime
import calendar
import json

#class LoggerConfig(AppConfig):
#    name = 'Logger'
def P(xx):
	print("_________"*5)
	for x in xx:
		print(x)
		print("\n")
	print("_________"*5)

class Statistic():
	__statProcessType = None
	__inputInfo = None
	__handleInfo = None
	__lastStatResult = None

	def __init__(self, processType, processInfo):
		self.__initStatProcess(processType, processInfo)

	def __initStatProcess(self, processType, processInfo):
		self.__statProcessType = processType
		self.__inputInfo = processInfo

		if processType in ['day','week','month','year']:
			data = models.RunLog.objects.filter(roomid = processInfo['roomid'])
			self.__handleInfo = [x.__dict__ for x in data]

			btime = None; etime = None
			if processType == 'day':
				btime = datetime.datetime.strptime(self.__inputInfo['btime'] + " 00:00:00", "%Y-%m-%d %H:%M:%S")
				etime = datetime.datetime.strptime(self.__inputInfo['btime'] + " 23:59:59", "%Y-%m-%d %H:%M:%S")
			elif processType == 'week':
				dt = datetime.datetime.strptime(self.__inputInfo['btime'] + " 00:00:00","%Y-%m-%d %H:%M:%S")
				weekday = dt.weekday()
				if weekday == 0:
					weekday = 7
				btime = dt - datetime.timedelta(days=weekday)
				etime = datetime.datetime.strptime(self.__inputInfo['btime'] + " 23:59:59","%Y-%m-%d %H:%M:%S") + datetime.timedelta(days=(7-weekday))
			elif processType == 'month':
				dt = datetime.datetime.strptime(self.__inputInfo['btime'] + " 00:00:00","%Y-%m-%d %H:%M:%S")
				monthday = calendar.monthrange(dt.year,dt.month)[1]
				btime = dt - datetime.timedelta(days=dt.day-1)
				etime = datetime.datetime.strptime(self.__inputInfo['btime'] + " 23:59:59","%Y-%m-%d %H:%M:%S") + datetime.timedelta(days=(monthday-dt.day))	
			elif processType == 'year':
				dt = datetime.datetime.strptime(self.__inputInfo['btime'] + " 00:00:00","%Y-%m-%d %H:%M:%S")
				yearday = 365
				if dt.year % 400 == 0 or (dt.year % 4 == 0 and dt.year % 100 != 0):
					yearday += 1
				noday = (dt - datetime.datetime.strptime(self.__inputInfo['btime'][:4] + "-01-01 00:00:00","%Y-%m-%d %H:%M:%S")).days
				btime = dt - datetime.timedelta(days=dt.day)
				etime = datetime.datetime.strptime(self.__inputInfo['btime'] + " 23:59:59","%Y-%m-%d %H:%M:%S") + datetime.timedelta(days=(noday-dt.day+1))	
			
			temp = []
			for row in self.__handleInfo:
				dt = datetime.datetime.strptime(str(row['currenttime']).split(".")[0],"%Y-%m-%d %H:%M:%S")
				if dt >= btime and dt <= etime:
					temp.append(row)
			self.__handleInfo = temp

		elif processType == 'invoice' or processType == 'record':
			data = models.RunLog.objects.filter(roomid = processInfo['roomid'])
			data = [x.__dict__ for x in data]
			self.__handleInfo = [data[-1]]
			for i in range(len(data)-2, -1, -1):
				temp = data[i]
				self.__handleInfo.append(temp)
				if temp['logtype'] == 'LOG_OTHER' and temp['flag'] == 'check_in':
					break
			self.__handleInfo = self.__handleInfo[::-1]
		else:
			pass 

	def __calFeeRate(self, item):
		return item['windspeed']

	def __calFee(self, item, duration):
		return self.__calFeeRate(item) * duration

	def __genReport(self):
		report = {'room_id': self.__inputInfo['roomid'], 'on_off_times': 0,
			      'service_time': 0, 'fee': 0, 'dispatch_times':0, 'rdr_number': 0,
			      'change_temp_times': 0, 'change_speed_times': 0}
		
		if len(self.__handleInfo) == 0:
			return report
		else:
			last = None
			for i, row in enumerate(self.__handleInfo):
				dt = datetime.datetime.strptime(str(row['currenttime']).split(".")[0],"%Y-%m-%d %H:%M:%S")
				if row['logtype'] == 'LOG_OTHER' and row['flag'] == "record":
					report['rdr_number'] += 1 
				if row['logtype'] == 'LOG_DISPATCH':
					report['dispatch_times'] += 1
				if row['flag'] == 'request_on' or row['flag'] == 'request_off':
					report['on_off_times'] += 1
				if last == None:
					if row['flag'] != 'check_in':
						return report
					last = row
				else:
					last_dt = datetime.datetime.strptime(str(last['currenttime']).split(".")[0],"%Y-%m-%d %H:%M:%S")
					print(last['flag'])
					if row['flag'] == "change_status":
						if row['windspeed'] != last['windspeed']:
							report['change_speed_times'] += 1
						if row['temperature'] != last['temperature']:
							report['change_temp_times'] += 1
					if last['flag'] in ['change_status', 'dispatch_on', 'air_out']:
						report['service_time'] += (dt - last_dt).seconds
					if last['flag'] in ['change_status', 'dispatch_on']:
						report['fee'] += self.__calFee(last, (dt - last_dt).seconds)
					last = row
		return report


	def handleStatProcess(self):
		
		if self.__statProcessType in ['day', 'week', 'month', 'year']:
			self.__lastStatResult = self.__genReport()		
		
		elif self.__statProcessType == 'invoice':
			result = {"room_id": self.__inputInfo['roomid'], "check_in_time":0,"check_out_time":0,"fee":0}
			last = None
			for row in self.__handleInfo:
				dt = datetime.datetime.strptime(str(row['currenttime']).split(".")[0],"%Y-%m-%d %H:%M:%S")
				if row['logtype'] == "LOG_OTHER" and row['flag'] == "check_in":
					result['check_in_time'] = str(dt)
				elif row['logtype'] == "LOG_OTHER" and row['flag'] == "check_out":
					result['check_out_time'] = str(dt)
				if last == None:
					if row['flag'] != 'check_in':
						break
					last = row
				else:
					last_dt = datetime.datetime.strptime(str(last['currenttime']).split(".")[0],"%Y-%m-%d %H:%M:%S")
					if last['flag'] in ['change_status', 'dispatch_on']:
						result['fee'] += self.__calFee(last, (dt - last_dt).seconds)
					last = row
			self.__lastStatResult = result

		elif self.__statProcessType == 'record':
			logger = Logger()
			logger.addLog({'roomid': self.__inputInfo['roomid'], 'temperature':0, 'windspeed':0, 'status':"HOT", "logtype":"LOG_OTHER", "flag":"record"})

			templete = {"roomid":self.__inputInfo['roomid'], 'start_time':0, "end_time":0, "speed":0, "target_temper":0, "fee":0, "fee_rate":0}
			
			last = None
			result = []
			
			for i, row in enumerate(self.__handleInfo):
				dt = datetime.datetime.strptime(str(row['currenttime']).split(".")[0],"%Y-%m-%d %H:%M:%S")
				if last == None:
					if row['flag'] != 'check_in':
						break
					last = row
				else:
					last_dt = datetime.datetime.strptime(str(last['currenttime']).split(".")[0],"%Y-%m-%d %H:%M:%S")
					if last['flag'] in ['change_status', 'dispatch_on']:
						temp = templete.copy()
						temp['start_time'] = str(last_dt)
						temp['end_time'] = str(dt)
						temp['fee'] = self.__calFee(last, (dt - last_dt).seconds)
						temp['speed'] = last['windspeed']
						temp['target_temper'] = last['temperature']
						temp['fee_rate'] = self.__calFeeRate(last)
						result.append(temp)
					last = row

			self.__lastStatResult = result

		return self.__lastStatResult

	def printStatResult(self):

		formatData = ""
		if self.__statProcessType != 'record':
			for k in self.__lastStatResult.keys():
				formatData += "{},{}\n".format(k, self.__lastStatResult[k])
		else:
			formatData += "btime, etime, speed, target, fee_rate, fee\n"
			for row in self.__lastStatResult:
				formatData += ",".join([str(row[k]) for k in row.keys()]) + '\n'

		return formatData

class Logger():
	def addLog(self, logInfo):
		models.RunLog.objects.create(**logInfo)

