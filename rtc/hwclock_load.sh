#!/bin/sh
while [ ! -e /dev/rtc ]; do echo 'hwclock not ready' && sleep 1; done
hwclock -s && echo "hwclock loaded -> $(date)" || { echo "hwclock cloud not be loaded"; hwclock --debug; exit 1; }
