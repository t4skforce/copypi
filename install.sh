#!/bin/bash
if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root"
   exit 1
fi
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

apt-get update -y \
  && apt-get upgrade -y \
  && apt-get install udisks-glue mosquitto mosquitto-clients i2c-tools ntfs-3g exfat-fuse exfat-utils usbutils python-dev python3-dev python-pip python3-pip \
  && apt-get clean \
  && apt-get autoclean || { echo "package install failed"; exit 1; }

# enable I2C on Raspberry Pi
echo '>>> Enable I2C and SPI'
if [ -f /boot/config.txt ]; then
  sed -i "s/^#\(dtparam=i2c1=on\).*/\1/" /boot/config.txt
  sed -i "s/^#\(dtparam=i2c_arm=on\).*/\1/" /boot/config.txt
  sed -i "s/^#\(dtparam=spi=on\).*/\1/" /boot/config.txt
fi
if [ -f /etc/modprobe.d/raspi-blacklist.conf ]; then
  sed -i 's/^\(blacklist*spi-*\)/#\1/' /etc/modprobe.d/raspi-blacklist.conf
  sed -i 's/^\(blacklist*i2c-*\)/#\1/' /etc/modprobe.d/raspi-blacklist.conf
fi

# install rtc-ds1307
echo '>> Installing rtc-ds1307'
modprobe rtc-ds1307 || { echo "module rtc-ds1307 could not be loaded"; exit 1; }
[[ -e "$DIR/rtc/rtc-i2c.conf" ]] && cp "$DIR/rtc/rtc-i2c.conf" /etc/rtc-i2c.conf && chmod 664 /etc/rtc-i2c.conf || { echo "cant find $DIR/rtc/rtc-i2c.conf"; exit 1; }
if [[ -e "/dev/i2c-1" ]]; then
  sed -i "s/\(BUS*=*\).*/\1\"1\"/" /etc/rtc-i2c.conf
else
  if [[ -e "/dev/i2c-0" ]]; then
    sed -i "s/\(BUS*=*\).*/\1\"0\"/" /etc/rtc-i2c.conf
  else
    echo "no i2c bus found"
    exit 1
  fi
fi
[[ -e "$DIR/rtc/rtc-i2c.service" ]] && cp "$DIR/rtc/rtc-i2c.service" /lib/systemd/system/rtc-i2c.service && chmod 664 /lib/systemd/system/rtc-i2c.service || { echo "cant find $DIR/rtc/rtc-i2c.service"; exit 1; }
[[ -e "$DIR/rtc/hwclock_load.sh" ]] && cp "$DIR/rtc/hwclock_load.sh" /usr/sbin/copypi-hwclock && chmod +x /usr/sbin/copypi-hwclock || { echo "$DIR/rtc/hwclock_load.sh"; exit 1; }
systemctl stop fake-hwclock.service && systemctl disable fake-hwclock.service || { echo "service fake-hwclock removal failed"; exit 1; }
systemctl daemon-reload && systemctl enable rtc-i2c.service && systemctl restart rtc-i2c.service || { echo "service install rtc-i2c.service failed"; journalctl -xe; exit 1; }
hwclock -w || { echo "could not set time on hwclock"; hwclock --debug; exit 1; }

# install mosquitto
echo '>> Installing mosquitto'
grep -q "bind_address" /etc/mosquitto/mosquitto.conf && sed -i 's/\(bind_address*\).*/\1 127.0.0.1/' /etc/mosquitto/mosquitto.conf || echo "bind_address 127.0.0.1" >> /etc/mosquitto/mosquitto.conf
grep -q "max_inflight_messages" /etc/mosquitto/mosquitto.conf && sed -i 's/\(max_inflight_messages*\).*/\1 0/' /etc/mosquitto/mosquitto.conf || echo "max_inflight_messages 0" >> /etc/mosquitto/mosquitto.conf
grep -q "max_queued_messages" /etc/mosquitto/mosquitto.conf && sed -i 's/\(max_queued_messages*\).*/\1 0/' /etc/mosquitto/mosquitto.conf || echo "max_queued_messages 0" >> /etc/mosquitto/mosquitto.conf
grep -q "persistence" /etc/mosquitto/mosquitto.conf && sed -i 's/\(persistence*\).*/\1 false/' /etc/mosquitto/mosquitto.conf || echo "persistence false" >> /etc/mosquitto/mosquitto.conf
systemctl enable mosquitto && systemctl restart mosquitto || { echo "service install mosquitto failed"; journalctl -xe; exit 1; }

# install python dependencies
echo '>> Installing python packages'
[[ -e "$DIR/copypi/requirements.txt" ]] && sudo -H /usr/bin/python3 -m pip install -r "$DIR/copypi/requirements.txt" || { echo "Error installing requirements"; exit 1; }

# install copypi-copy
echo '>> Installing copypi-copy'
[[ -e "$DIR/copypi/copypi-copy.service" ]] && cp "$DIR/copypi/copypi-copy.service" /lib/systemd/system/copypi-copy.service && chmod 664 /lib/systemd/system/copypi-copy.service || { echo "cant find /lib/systemd/system/copypi-copy.service"; exit 1; }
[[ -e "$DIR/copypi/copypi-copy.py" ]] && cp "$DIR/copypi/copypi-copy.py" /usr/sbin/copypi-copy && chmod +x /usr/sbin/copypi-copy || { echo "cant find $DIR/copypi/copypi-copy.py"; exit 1; }
systemctl daemon-reload && systemctl enable copypi-copy.service && systemctl restart copypi-copy.service || { echo "service install copypi-copy.service failed"; journalctl -xe; exit 1; }

# install copypi-status
echo '>> Installing copypi-status'
[[ -e "$DIR/copypi/copypi-status.service" ]] && cp "$DIR/copypi/copypi-status.service" /lib/systemd/system/copypi-status.service && chmod 664 /lib/systemd/system/copypi-status.service || { echo "cant find /lib/systemd/system/copypi-status.service"; exit 1; }
[[ -e "$DIR/copypi/copypi-status.py" ]] && cp "$DIR/copypi/copypi-status.py" /usr/sbin/copypi-status && chmod +x /usr/sbin/copypi-status || { echo "cant find $DIR/copypi/copypi-status.py"; exit 1; }
systemctl daemon-reload && systemctl enable copypi-status.service && systemctl restart copypi-status.service || { echo "service install copypi-status.service failed"; journalctl -xe; exit 1; }

# install copypi-display
echo '>> Installing copypi-display'
[[ -e "$DIR/copypi/copypi-display.service" ]] && cp "$DIR/copypi/copypi-display.service" /lib/systemd/system/copypi-display.service && chmod 664 /lib/systemd/system/copypi-display.service || { echo "cant find /lib/systemd/system/copypi-display.service"; exit 1; }
[[ -e "$DIR/copypi/copypi-display.py" ]] && cp "$DIR/copypi/copypi-display.py" /usr/sbin/copypi-display && chmod +x /usr/sbin/copypi-display || { echo "cant find $DIR/copypi/copypi-display.py"; exit 1; }
systemctl daemon-reload && systemctl enable copypi-display.service && systemctl restart copypi-display.service || { echo "service install copypi-display.service failed"; journalctl -xe; exit 1; }

# install copypi-mount
echo '>> Installing copypi-mount'
[[ -e "$DIR/copypi/copypi-mount.py" ]] && cp "$DIR/copypi/copypi-mount.py" /usr/sbin/copypi-mount && chmod +x /usr/sbin/copypi-mount || { echo "cant find $DIR/copypi/copypi-mount.py"; exit 1; }

# install udisks-glue
echo '>> Installing udisks-glue'
[[ -e "$DIR/udisks-glue/udisks-glue.conf" ]] && cp "$DIR/udisks-glue/udisks-glue.conf" /etc/udisks-glue.conf && chmod 664 /etc/udisks-glue.conf || { echo "cant find $DIR/udisks-glue/udisks-glue.conf"; exit 1; }
[[ -e "$DIR/udisks-glue/udisks-glue.service" ]] && cp "$DIR/udisks-glue/udisks-glue.service" /lib/systemd/system/udisks-glue.service && chmod 664 /lib/systemd/system/udisks-glue.service || { echo "cant find /lib/systemd/system/udisks-glue.service"; exit 1; }
systemctl daemon-reload && systemctl enable udisks-glue.service && systemctl restart udisks-glue.service || { echo "service install udisks-glue.service failed"; journalctl -xe; exit 1; }
