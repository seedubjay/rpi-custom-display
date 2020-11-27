apt-get install python3-pip libopenjp2-7 libtiff5
pip3 install luma.core luma.oled lifxlan

cp custom-display.service /etc/systemd/system/custom-display.service
systemctl enable custom-display
systemctl start custom-display