#!/bin/bash
if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root"
   exit 1
fi
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

rm -f /usr/sbin/copypi-copy
rm -f /usr/sbin/copypi-status
rm -f /usr/sbin/copypi-display
rm -f /usr/sbin/copypi-mount

ln -s "$DIR/copypi/copypi-copy.py" /usr/sbin/copypi-copy
ln -s "$DIR/copypi/copypi-status.py" /usr/sbin/copypi-status
ln -s "$DIR/copypi/copypi-display.py" /usr/sbin/copypi-display
ln -s "$DIR/copypi/copypi-mount.py" /usr/sbin/copypi-mount
systemctl daemon-reload && systemctl restart copypi-copy
systemctl daemon-reload && systemctl restart copypi-status
systemctl daemon-reload && systemctl restart copypi-display
systemctl daemon-reload && systemctl restart udisks-glue
