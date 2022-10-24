#!/bin/bash

ps -gauxww | grep [r]pi_jukebox.py > /dev/null 2>&1
if [ $? -eq 1 ]
then
  nohup /usr/bin/python -u /home/pi/rpi_jukebox/rpi_jukebox.py --config /home/pi/rpi_jukebox/rpi_jukebox.config >> /home/pi/rpi_jukebox/jukebox.log 2>&1 &
fi