blacklist_end=$(ssh pi@192.168.2.204 'cat blacklist_end')
epoch=$(date +%s)

w=$(( blacklist_end - epoch ))

if [ $w -gt 0 ]; then
    echo "blacklist activated for" $w "seconds"
    pihole --wild $(cat /home/pi/blacklist.txt)
    systemctl stop lighttpd
    echo "blacklist loaded"

    sleep $w

    pihole --wild -d $(cat /home/pi/blacklist.txt)
    systemctl start lighttpd
fi