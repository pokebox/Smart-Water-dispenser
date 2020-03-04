# 智能饮水机

这是个智能饮水机项目，整个项目使用Python3编写。

器件清单：

| 名称                  | 数量 |
| --------------------- | ---- |
| 树莓派                | 1    |
| ILI9341 TFT 2.2寸屏幕 | 1    |
| 4x4矩阵键盘           | 1    |
| DS18B20温度传感器     | 1    |
| HC-SR04超声波传感器   | 1    |
| DS1307时钟            | 1    |
| 12V水泵               | 1    |
| 12V加热器             | 1    |
| 3V继电器              | 2    |
| 三极管                | 3    |
| 12V电源               | 1    |
| DC-DC5V降压模块       | 1    |

首次使用前，先获取项目里的install.sh脚本，运行安装基本环境，然后可以根据实际情况，将项目写到开机启动脚本中。

在一个固定目录里编写一个运行脚本，假设在/home/pi中创建一个run_ysj.sh文件，然后写入：

```bash
#!/bin/bash

if [ -e /home/pi/Smart-Water-dispenser ];then
	cd /home/pi/Smart-Water-dispenser
	while :
	do
		. ./export.sh
		python3 ./main.py $LUMA_ILI9341
	done
	git checkout -- .
	git pull
else
	git clone git@github.com:pokebox/Smart-Water-dispenser.git
	ntpdate ntp1.aliyun.com
	hwclock -w
fi
```

赋予文件执行权限，然后在/etc/rc.local脚本中添加一行`/home/pi/run_ysj.sh &`

运行项目还需要开启SPI、IIC、W1-Bus，使用raspi-config设置相关的选项保证硬件功能开启。