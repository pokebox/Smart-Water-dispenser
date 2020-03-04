#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pad4pi import rpi_gpio
import RPi.GPIO as GPIO

class keyboard():
    def __init__(self):
        GPIO.setmode(GPIO.BCM)
        KEYPAD = [
            ["1","2","3","A"],
            ["4","5","6","B"],
            ["7","8","9","C"],
            ["*","0","#","D"]
        ]
        if True:    # 正向安装True，方向安装False
            ROW_PINS = [12, 16, 20, 21] ##行BCM引脚号
            COL_PINS = [6 , 13, 19, 26] ##列BCM引脚号
        else:
            ROW_PINS = [26, 19, 13, 6 ] ##行BCM引脚号
            COL_PINS = [21, 20, 16, 12] ##列BCM引脚号

        factory = rpi_gpio.KeypadFactory()
        keypad = factory.create_keypad(keypad=KEYPAD, row_pins=ROW_PINS, col_pins=COL_PINS)
        keypad.registerKeyPressHandler(self.keyout)
        self.key=None
        self.havekey=False

    def keyout(self,key):
        self.havekey=True
        self.key=key
