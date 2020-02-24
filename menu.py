#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import time
from luma.core.render import canvas

class Menu:
    def __init__(self, title, title_color='white', title_bg_color='black'):
        self.title = title
        self.title_color = title_color
        self.title_bg_color = title_bg_color
        self.menu_list = {}

class OptionMenu(Menu):
    def __init__(self, title, keyboard, device, cur='->', title_color='white',
                 title_bg_color='black', cur_color='white',
                 cur_bg_color='black', font=None):
        super().__init__(title, title_color, title_bg_color)
        self.cur = cur
        self.cur_color = cur_color
        self.cur_bg_color = cur_bg_color
        self.keyboard=keyboard
        self.font=font
        self.device=device

    def _print_screen(self, selected):
        with canvas(self.device) as draw:
            draw.text((0,1), self.title, font=self.font, fill="green")
            for index, (option, _) in enumerate(self.menu_list.items()):
                x = len(self.cur)
                y = index + 1
                option_color = index + 3
                cur_add = self.font.getsize(self.cur)
                cur_add_x = cur_add[1]
                cur_add_y = cur_add[1] + 1

                if index == selected:
                    draw.text((0,y*cur_add_y), self.cur, font=self.font, fill="white")
                    draw.text((x*cur_add_x,y*cur_add_y), option, font=self.font, fill="white")
                else:
                    draw.text((x*cur_add_x,y*cur_add_y), option, font=self.font, fill="red")


    def add_option(self, option, color='white', bg_color='black', ret=None):
        self.menu_list.update({option: {'color': color,
                                        'bg_color': bg_color,
                                        'ret': ret}})

    def _run(self):
        for index, (_, settings) in enumerate(self.menu_list.items()):
            index += 3

        selected = 0

        while True:
            self._print_screen(selected)

            while self.keyboard.havekey == False:
                time.sleep(0.01)
            self.keyboard.havekey=False
            key = self.keyboard.key

            if key == "A" and selected > 0:
                selected -= 1
            elif key == "B" and selected < len(self.menu_list)-1:
                selected += 1
            elif key == "#" or key in [10, 13]:
                for index, (option,
                            settings) in enumerate(self.menu_list.items()):
                    if index == selected:
                        return settings['ret'] if settings['ret'] else option
                break

    def run(self):
        selected_option = self._run()
        return selected_option
