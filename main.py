#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time,datetime
import RPi.GPIO as GPIO
# 界面处理
from demo_opts import get_device
from luma.core.virtual import terminal
from luma.core.render import canvas
from PIL import ImageFont
from menu import *
from keyboard import *
# 线程操作
from threading import Thread
# 传感器
from DS18B20 import *
from HCSR04 import *

def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        pass

    try:
        import unicodedata
        unicodedata.numeric(s)
        return True
    except (TypeError, ValueError):
        pass

    return False

def minNums(startTime, endTime):
    '''计算两个时间点之间的分钟数'''
    startTime2 = datetime.datetime.strptime(startTime, "%Y-%m-%d %H:%M:%S")
    endTime2 = datetime.datetime.strptime(endTime, "%Y-%m-%d %H:%M:%S")
    seconds = (endTime2 - startTime2).seconds
    # 来获取时间差中的秒数。注意，seconds获得的秒只是时间差中的小时、分钟和秒部分的和，并没有包含时间差的天数（既是两个时间点不是同一天，失效）
    total_seconds = (endTime2 - startTime2).total_seconds()
    # 来获取准确的时间差，并将时间差转换为秒
    mins = total_seconds / 60
    return int(mins)

class ysj(object):
    def __init__(self,device, keyboard):
        GPIO.setmode(GPIO.BCM)
        self.gpio_beep      = 22    ##蜂鸣器GPIO，自行设置
        self.gpio_heating   = 23    ##加热器电源IO，自行设置
        self.gpio_pump      = 5     ##水泵
        GPIO.setup(self.gpio_beep, GPIO.OUT)
        GPIO.setup(self.gpio_heating, GPIO.OUT)
        GPIO.setup(self.gpio_pump, GPIO.OUT)
        GPIO.output(self.gpio_beep, False)
        GPIO.output(self.gpio_heating, True)
        GPIO.output(self.gpio_pump, True)

        self.device=device
        self.keyboard=keyboard
        self.mode=0 #模式状态：0正常，1加热设置（温度，水量，时间），2保温设定（温度，水量，时段）
        self.M_SAVETEMP='savetemp'
        self.M_HEATING='heating'
        self.W_DRYHEAT='DryHeat'    ##干烧状态
        self.heatMode=None
        self.start_saveTemp='1970-01-01 00:00:00'
        self.Container_height=10        ##容器高度

        # 加热设定初值
        self.hot_h          = 0 ##加热时间
        self.hot_m          = 0
        self.hot_s          = 0
        self.hot_temp       = 70 ##加热温度
        self.hot_waterVol   = 0 ##加热水量

        # 保温设定初值
        self.saveTemp           = 0 ##保温温度
        self.saveTemp_m         = 0 ##保温时间
        self.saveTemp_watterVol = 0 ##保温水量

        self.DryTime            = 1 ##干烧超时时间（分钟）

        # 初始化传感器
        self.ds18b20    = DS18B20()
        self.hcsr04     = HCSR04()

        self.temp       = self.ds18b20.read_temp()
        self.waterLevel = self.Container_height - self.hcsr04.distance()

        self.old_temp=self.temp

        # 初始化线程
        self.th_temp = Thread(target=self.gettemp)
        self.th_temp.setDaemon(True)

        self.th_hc04 = Thread(target=self.gethcsr04)
        self.th_hc04.setDaemon(True)

        self.th_heating = Thread(target=self.heatingTask)
        self.th_heating.setDaemon(True)

    def make_font(self, name, size):
        font_path = os.path.abspath(os.path.join(
            os.path.dirname(__file__), 'fonts', name))
        return ImageFont.truetype(font_path, size)

    def gettemp(self):  ##读取温度数据
        while True:
            self.temp=self.ds18b20.read_temp()
            time.sleep(2)

    def gethcsr04(self):    ##读取超声波传感器数据
        while True:
            self.waterLevel=self.Container_height - self.hcsr04.distance()
            time.sleep(0.5)

    def heatingTask(self):
        while True:
            if self.hot_h == int(time.strftime("%H", time.localtime())):
                if self.hot_m == int(time.strftime("%M", time.localtime())):
                    if self.hot_s == int(time.strftime("%S", time.localtime())):
                        # 判断温度和水位达到加热要求并且当前没在加热
                        if (self.temp <= self.hot_temp) and (self.heatMode != self.M_HEATING):
                            while self.waterLevel <= self.hot_waterVol:
                                self.setPump(True)      ##打开水阀加水
                            self.heatMode=self.M_HEATING  ##加热模式
                            self.setPump(False)         ##关闭水阀
                            self.setHeating(True)       ##加热
                            #self.setBeep(0.2)         #蜂鸣器
            # 水温高于设置值时关闭加热器
            if self.temp >= self.hot_temp and self.heatMode == self.M_HEATING:
                self.setHeating(False)
                # 如果是加热完成就提示
                if self.heatMode == self.M_HEATING:
                    # 跳到保温模式
                    self.heatMode = self.M_SAVETEMP
                    self.start_saveTemp = self.nowTime()
                    self.setBeep(0.2, 0.1)
                    self.setBeep(0.2, 0.1)
                    self.setBeep(0.2, 0.1)
            # 如果是保温模式
            elif self.heatMode == self.M_SAVETEMP:
                if self.temp >= self.saveTemp:
                    self.setHeating(False)
                else:
                    self.setHeating(True)

            # 如果保温时间超过设定时间则停止保温
            if ((minNums(self.start_saveTemp, self.nowTime()) >= self.saveTemp_m)
                and (self.heatMode == self.M_SAVETEMP)):
                self.heatMode = None

            # 如果当前加热器在工作
            if self.isHeating():
                ## 判断温度是否变化超过1度，如果没变化，看看是否加热了一段时间
                if (self.temp-self.old_temp) < 1:
                    if (minNums(self.start_Heating, self.nowTime()) >= self.DryTime):
                        #干烧报警
                        self.heatMode = self.W_DRYHEAT
                        self.setHeating(False)
                        self.setBeep(2,0.5)
                else:
                    self.old_temp=self.temp
                    self.start_Heating=self.nowTime()

            time.sleep(0.2)

    def setHeating(self, open):     ##加热棒
        GPIO.setup(self.gpio_heating, GPIO.OUT)
        if not open:
            try:
                GPIO.output(self.gpio_heating, True)
            except err:
                pass
        else:
            try:
                GPIO.output(self.gpio_heating, False)
            except err:
                pass
        ##如果设置为加热
        if open:
            self.start_Heating=self.nowTime()
        else:
            self.start_Heating=None

    def isHeating(self):
        return not GPIO.input(self.gpio_heating)

    def setBeep(self, timestart, timestop=None):        ##蜂鸣器
        GPIO.setup(self.gpio_beep, GPIO.OUT)
        GPIO.output(self.gpio_beep, True)
        time.sleep(timestart)
        GPIO.output(self.gpio_beep, False)
        if timestop != None:
            time.sleep(timestop)

    def setPump(self, open):
        GPIO.setup(self.gpio_pump, GPIO.OUT)
        if not open:
            GPIO.output(self.gpio_pump, True)
        else:
            GPIO.output(self.gpio_pump, False)

    def nowTime(self):
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

    def main(self):
        font = self.make_font("wqy-zenhei.ttc", 24)
        font_size = font.getsize(u"水")[1]

        self.th_temp.start()
        self.th_hc04.start()
        self.th_heating.start()

        # 主循环
        while True:
            # 等待按键操作期间刷新默认屏幕
            while self.keyboard.havekey == False:
                with canvas(self.device) as draw:
                    draw.text((0,0), u"饮水机", font=font, fill="white")
                    draw.text((font.getsize(u"饮水机 ")[0],0), time.strftime("%H:%M:%S", time.localtime()), font=font, fill="yellow")
                    draw.text((0,font_size*1), "水温：{0:0.1f} ℃".format(self.temp), font=font, fill="green")
                    draw.text((0,font_size*2), "水位：{0:0.1f} cm".format(self.waterLevel), font=font, fill="blue")
                    draw.text((0,font_size*3), "状态：", font=font, fill="white")
                    if (self.heatMode == self.M_HEATING and self.isHeating()):
                        draw.text((font.getsize(u"状态： ")[0],font_size*3), "正在加热", font=font, fill="red")
                    elif (self.heatMode == self.M_SAVETEMP):
                        draw.text((font.getsize(u"状态： ")[0],font_size*3), "正在保温", font=font, fill="green")
                    elif (self.heatMode == self.W_DRYHEAT):
                        draw.text((font.getsize(u"状态： ")[0],font_size*3), "干烧报警！", font=font, fill=(255,50,255))
                    else:
                        draw.text((font.getsize(u"状态： ")[0],font_size*3), "待机", font=font, fill=(80,80,80))

            # 有按键输入，重置标志位
            self.keyboard.havekey=False
            # 判断按下的是#键则进入菜单
            if self.keyboard.key == "#":
                ret=ret2=ret3=None
                while ret != -1:
                    menu_1=OptionMenu(u"功能列表", self.keyboard, self.device, font=font)
                    menu_1.add_option(u"加热设置", ret=1)
                    menu_1.add_option(u"保温设定", ret=2)
                    if self.heatMode == self.W_DRYHEAT:
                        menu_1.add_option(u"解除报警", ret=3)
                    menu_1.add_option(u"返回", ret=-1)
                    ret=menu_1.run()
                    if ret == 1:    # 加热设置目录
                        menu_2=OptionMenu(u"加热设置", self.keyboard, self.device, font=font)
                        menu_2.add_option(u"加热时间", ret=1)
                        menu_2.add_option(u"加热温度", ret=2)
                        menu_2.add_option(u"加热水量", ret=3)
                        menu_2.add_option(u"返回", ret=-1)
                        ret2=menu_2.run()
                        if ret2 == 1:   # 加热时间设置
                            add_mode=1
                            while True:
                                with canvas(self.device) as draw:
                                    draw.text((0,0), u"加热时间设置", font=font)
                                    draw.text((0,font_size*1), u"{0:02d}:{1:02d}:{2:02d}".format(self.hot_h, self.hot_m, self.hot_s), font=font)
                                    draw.text((0,font_size*2), u"#确定", font=font)
                                # 等待按键按下
                                while self.keyboard.havekey == False:
                                    time.sleep(0.01)
                                # 复位按键标识符
                                self.keyboard.havekey = False
                                # 判断按下的是数字键
                                if is_number(self.keyboard.key):
                                    if add_mode == 1:
                                        hot_hh=int(self.keyboard.key)
                                        if hot_hh <= 2:
                                            self.hot_h=hot_hh*10
                                            add_mode += 1
                                    elif add_mode == 2:
                                        hot_hl=int(self.keyboard.key)
                                        self.hot_h=hot_hh*10+hot_hl
                                        add_mode += 1
                                    elif add_mode == 3:
                                        hot_mh=int(self.keyboard.key)
                                        if hot_mh <= 5:
                                            self.hot_m=hot_mh*10
                                            add_mode += 1
                                    elif add_mode == 4:
                                        hot_ml=int(self.keyboard.key)
                                        self.hot_m=hot_mh*10+hot_ml
                                        add_mode += 1
                                    elif add_mode == 5:
                                        hot_sh=int(self.keyboard.key)
                                        if hot_sh <= 5:
                                            self.hot_s=hot_sh*10
                                            add_mode += 1
                                    elif add_mode == 6:
                                        hot_sl=int(self.keyboard.key)
                                        self.hot_s=hot_sh*10+hot_sl
                                        add_mode += 1
                                    elif add_mode >= 7:
                                        break
                                    print(add_mode)
                                elif self.keyboard.key == "#":
                                    break
                        elif ret2 == 2: # 加热温度设置
                            add_mode=1
                            while True:
                                with canvas(self.device) as draw:
                                    draw.text((0,0), u"加热温度设置", font=font)
                                    draw.text((0,font_size*1), u"{0:02d} ℃".format(self.hot_temp), font=font)
                                    draw.text((0,font_size*2), u"#确定", font=font)
                                # 等待按键按下
                                while self.keyboard.havekey == False:
                                    time.sleep(0.01)
                                # 复位按键标识符
                                self.keyboard.havekey = False
                                # 判断按下的是数字键
                                if is_number(self.keyboard.key):
                                    if add_mode == 1:
                                        self.hot_temp=int(self.keyboard.key)
                                        add_mode += 1
                                    elif add_mode == 2:
                                        self.hot_temp=self.hot_temp*10+int(self.keyboard.key)
                                        add_mode += 1
                                    elif add_mode >= 3:
                                        break
                                    print(add_mode)
                                elif self.keyboard.key == "#":
                                    break
                        elif ret2 == 3: # 加热水量设置
                            add_mode=1
                            while True:
                                with canvas(self.device) as draw:
                                    draw.text((0,0), u"加热水量设置", font=font)
                                    draw.text((0,font_size*1), u"{0:02d} cm".format(self.hot_waterVol), font=font)
                                    draw.text((0,font_size*2), u"#确定", font=font)
                                # 等待按键按下
                                while self.keyboard.havekey == False:
                                    time.sleep(0.01)
                                # 复位按键标识符
                                self.keyboard.havekey = False
                                # 判断按下的是数字键
                                if is_number(self.keyboard.key):
                                    if add_mode == 1:
                                        self.hot_waterVol=int(self.keyboard.key)
                                        add_mode += 1
                                    elif add_mode == 2:
                                        self.hot_waterVol=self.hot_waterVol*10+int(self.keyboard.key)
                                        add_mode += 1
                                    elif add_mode >= 3:
                                        break
                                    print(add_mode)
                                elif self.keyboard.key == "#":
                                    break

                    elif ret == 2:  # 保温设置目录
                        menu_3=OptionMenu(u"保温设定", self.keyboard, self.device, font=font)
                        menu_3.add_option(u"保温时间", ret=1)
                        menu_3.add_option(u"保温温度", ret=2)
                        menu_3.add_option(u"保温水量", ret=3)
                        menu_3.add_option(u"返回", ret=-1)
                        ret3=menu_3.run()
                        if ret3 == 1:   # 保温时间设置
                            add_mode=1
                            while True:
                                with canvas(self.device) as draw:
                                    draw.text((0,0), u"保温时间设置", font=font)
                                    draw.text((0,font_size*1), u"{0:04d} 分钟".format(self.saveTemp_m), font=font)
                                    draw.text((0,font_size*2), u"#确定", font=font)
                                # 等待按键按下
                                while self.keyboard.havekey == False:
                                    time.sleep(0.01)
                                # 复位按键标识符
                                self.keyboard.havekey = False
                                # 判断按下的是数字键
                                if is_number(self.keyboard.key):
                                    if add_mode == 1:
                                        self.saveTemp_m=int(self.keyboard.key)
                                        add_mode += 1
                                    elif add_mode >= 2 and add_mode <= 4:
                                        self.saveTemp_m=self.saveTemp_m*10+int(self.keyboard.key)
                                        add_mode += 1
                                        if self.saveTemp_m > 1440:
                                            self.saveTemp_m=1440
                                    elif add_mode >= 5:
                                        break
                                elif self.keyboard.key == "#":
                                    break
                        elif ret3 == 2: # 保温温度设置
                            add_mode=1
                            while True:
                                with canvas(self.device) as draw:
                                    draw.text((0,0), u"保温温度设置", font=font)
                                    draw.text((0,font_size*1), u"{0:02d} ℃".format(self.saveTemp), font=font)
                                    draw.text((0,font_size*2), u"#确定", font=font)
                                # 等待按键按下
                                while self.keyboard.havekey == False:
                                    time.sleep(0.01)
                                # 复位按键标识符
                                self.keyboard.havekey = False
                                # 判断按下的是数字键
                                if is_number(self.keyboard.key):
                                    if add_mode == 1:
                                        self.saveTemp=int(self.keyboard.key)
                                        add_mode += 1
                                    elif add_mode == 2:
                                        self.saveTemp=self.saveTemp*10+int(self.keyboard.key)
                                        add_mode += 1
                                    elif add_mode >= 3:
                                        break
                                    print(add_mode)
                                elif self.keyboard.key == "#":
                                    break
                        elif ret3 == 3: # 保温水量设置
                            add_mode=1
                            while True:
                                with canvas(self.device) as draw:
                                    draw.text((0,0), u"保温水量设置", font=font)
                                    draw.text((0,font_size*1), u"{0:02d} cm".format(self.saveTemp_watterVol), font=font)
                                    draw.text((0,font_size*2), u"#确定", font=font)
                                # 等待按键按下
                                while self.keyboard.havekey == False:
                                    time.sleep(0.01)
                                # 复位按键标识符
                                self.keyboard.havekey = False
                                # 判断按下的是数字键
                                if is_number(self.keyboard.key):
                                    if add_mode == 1:
                                        self.saveTemp_watterVol=int(self.keyboard.key)
                                        add_mode += 1
                                    elif add_mode == 2:
                                        self.saveTemp_watterVol=self.saveTemp_watterVol*10+int(self.keyboard.key)
                                        add_mode += 1
                                    elif add_mode >= 3:
                                        break
                                    print(add_mode)
                                elif self.keyboard.key == "#":
                                    break
                    elif ret == 3:
                        self.heatMode=None
                        break
                    elif ret == 0:
                        break
                self.keyboard.havekey=False

            elif self.keyboard.key == "A":  # 加热开关
                if self.heatMode == self.M_HEATING:
                    self.heatMode = None
                    self.setHeating(False)
                elif self.heatMode == self.W_DRYHEAT:
                    pass
                else:
                    self.heatMode = self.M_HEATING
                    self.setHeating(True)
            elif self.keyboard.key == "B":  # 保温开关
                if self.heatMode == self.M_SAVETEMP:
                    self.heatMode = None
                    self.setHeating(False)
                elif self.heatMode == self.W_DRYHEAT:
                    pass
                else:
                    self.start_saveTemp = self.nowTime()
                    self.heatMode = self.M_SAVETEMP
                    self.setHeating(True)

            time.sleep(0.2)


globalKeyboard=keyboard()
if __name__ == "__main__":
    try:
        device = get_device()
        app=ysj(device, globalKeyboard)
        app.main()
    except KeyboardInterrupt:
        pass
