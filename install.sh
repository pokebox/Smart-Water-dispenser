#!/bin/bash
# 饮水机环境安装脚本
usermod -a -G spi,gpio pi
cp /etc/apt/sources.list /etc/apt/sources.list.bf
sed -i 's/raspbian.raspberrypi.org/mirrors.cloud.tencent.com\/raspbian/g' /etc/apt/sources.list
apt update
apt install -y git cmake libssl-dev gcc g++ automake bc htop jq
apt install -y python-dev python-pip libfreetype6-dev libjpeg-dev build-essential libopenjp2-7 libtiff5
apt install -y libavutil-dev libavutil56 libavcodec58 libavcodec-dev libavformat-dev libavformat58 libavfilter-dev libavdevice-dev
apt install -y ttf-wqy-zenhei
#cp /usr/share/fonts/truetype/wqy/wqy-zenhei.ttc ./
pip3 install --upgrade pip
pip3 install Adafruit_GPIO
pip3 install --upgrade luma.lcd luma.core luma.oled
pip3 install --upgrade pad4pi

#pip3 install av psutil
#pip3 install pusherclient tweepy feedparser

git clone https://github.com/pokebox/Smart-Water-dispenser.git
