#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
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

class ysj(object):
    def __init__(self,device, keyboard):
        GPIO.setmode(GPIO.BCM)
        self.gpio_beep      = 22    ##蜂鸣器GPIO，自行设置
        self.gpio_heating   = 18    ##加热器电源IO，自行设置

        self.device=device
        self.keyboard=keyboard
        self.mode=0 #模式状态：0正常，1加热设置（温度，水量，时间），2保温设定（温度，水量，时段）

        # 加热设定初值
        self.hot_h          = 0 ##加热时间
        self.hot_m          = 0
        self.hot_s          = 0
        self.hot_temp       = 70 ##加热温度
        self.hot_waterVol   = 0 ##加热水量

        # 初始化传感器
        self.ds18b20    = DS18B20()
        self.hcsr04     = HCSR04()

        self.temp       = self.ds18b20.read_temp()
        self.waterLevel = self.hcsr04.distance()
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
            time.sleep(5)

    def gethcsr04(self):    ##读取超声波传感器数据
        while True:
            self.waterLevel=self.hcsr04.distance()
            time.sleep(0.5)

    def heatingTask(self):
        while True:
            if self.hot_h == int(time.strftime("%H", time.localtime())):
                if self.hot_m == int(time.strftime("%M", time.localtime())):
                    if self.hot_s == int(time.strftime("%S", time.localtime())):
                        # 判断温度和水位达到加热要求并且当前没在加热
                        print(u"开始加热")
                        print(self.isHeating())
                        if self.temp <= self.hot_temp and self.isHeating() == False:
                                self.setBeep(True)
                                self.setHeating(True)
                                time.sleep(0.5)
                                self.setBeep(False)
            time.sleep(0.2)

    def setHeating(self, open):     ##加热棒
        GPIO.setup(self.gpio_heating, GPIO.OUT)
        if open:
            try:
                GPIO.output(self.gpio_heating, True)
            except err:
                pass
        else:
            try:
                GPIO.output(self.gpio_heating, False)
            except err:
                pass

    def isHeating(self):
        return GPIO.input(self.gpio_heating)

    def setBeep(self, open):        ##蜂鸣器
        GPIO.setup(self.gpio_beep, GPIO.OUT)
        if open:
            GPIO.output(self.gpio_beep, True)
        else:
            GPIO.output(self.gpio_beep, False)


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
                    draw.text((font.getsize(u"饮水机 ")[0],0), time.strftime("%H:%M:%S", time.localtime()), font=font, fill="red")
                    draw.text((0,font_size*1), "水温：{0:0.1f} ℃".format(self.temp), font=font, fill="green")
                    draw.text((0,font_size*2), "水位：{0:0.1f} cm".format(self.waterLevel), font=font, fill="blue")

            # 有按键输入，重置标志位
            self.keyboard.havekey=False
            # 判断按下的是#键则进入菜单
            if self.keyboard.key == "#":
                ret=None
                while ret != -1:
                    print(font.getsize(u"功能列表"))
                    menu_1=OptionMenu(u"功能列表", self.keyboard, self.device, font=font)
                    menu_1.add_option(u"加热设置", ret=1)
                    menu_1.add_option(u"保温设定", ret=2)
                    menu_1.add_option(u"时间校准", ret=3)
                    menu_1.add_option(u"返回", ret=-1)
                    ret=menu_1.run()
                    print(ret)
                    if ret == 1:
                        menu_2=OptionMenu(u"加热设置", self.keyboard, self.device, font=font)
                        menu_2.add_option(u"加热时间", ret=1)
                        menu_2.add_option(u"加热温度", ret=2)
                        menu_2.add_option(u"加热水量", ret=3)
                        menu_2.add_option(u"返回", ret=-1)
                        ret2=menu_2.run()
                        print(ret2)
                        if ret2 == 1:
                            add_mode=1
                            while True:
                                with canvas(self.device) as draw:
                                    draw.text((0,0), u"加热时间设置", font=font)
                                    draw.text((0,font_size*1), u"{0}:{1}:{2}".format(self.hot_h, self.hot_m, self.hot_s), font=font)
                                    draw.text((0,font_size*2), u"#确定 AD上下 BC左右", font=font)
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
                        elif ret2 == 2:
                            add_mode=1
                            while True:
                                with canvas(self.device) as draw:
                                    draw.text((0,0), u"加热温度设置", font=font)
                                    draw.text((0,font_size*1), u"{0}".format(self.hot_temp), font=font)
                                    draw.text((0,font_size*2), u"#确定 AD上下 BC左右", font=font)
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
                        elif ret2 == 3:
                            add_mode=1
                            while True:
                                with canvas(self.device) as draw:
                                    draw.text((0,0), u"加热水量设置", font=font)
                                    draw.text((0,font_size*1), u"{0} cm".format(self.hot_waterVol), font=font)
                                    draw.text((0,font_size*2), u"#确定 AD上下 BC左右", font=font)
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

                    elif ret == 2:
                        menu_3=OptionMenu(u"保温设定", self.keyboard, self.device, font=font)
                        menu_3.add_option(u"保温时段", ret=1)
                        menu_3.add_option(u"保温温度", ret=2)
                        menu_3.add_option(u"保温水量", ret=3)
                        menu_3.add_option(u"返回", ret=-1)
                        ret3=menu_3.run()
                        print(ret3)
                    elif ret == 0:
                        break
                self.keyboard.havekey=False

            elif self.keyboard.key == "A":  # 加热开关
                if self.isHeating():
                    self.setHeating(False)
                else:
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
