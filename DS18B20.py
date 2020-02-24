#-*- coding:utf-8 -*-
import os,time

class DS18B20:
    def __init__(self):
        self.device_file ='/sys/bus/w1/devices/28-0115726f58ff/w1_slave'
        self.temp=0

    def read_temp_raw(self):
        f = open(self.device_file,'r')
        lines = f.readlines()
        f.close()
        return lines

    def read_temp(self):
        lines = self.read_temp_raw()
        while lines[0].strip()[-3:] != 'YES':
            time.sleep(0.2)
            lines = self.read_temp_raw()
        equals_pos = lines[1].find('t=')
        if equals_pos != -1:
            temp_string = lines[1][equals_pos+2:]
            temp_c = float(temp_string)/1000.0
        self.temp=temp_c
        return temp_c

#while True:
#    print('temp C = %f'%read_temp())
#    time.sleep(1)
