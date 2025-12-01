#!/bin/bash
echo "========================================"
echo "🥧 Raspberry Pi Network Diagnostic Tool"
echo "========================================"

echo "\n[1] Checking IP Address..."
hostname -I

echo "\n[2] Checking Internet Connectivity (Ping 8.8.8.8)..."
ping -c 4 8.8.8.8
if [ $? -eq 0 ]; then
    echo "✅ Internet Connection: OK"
else
    echo "❌ Internet Connection: FAILED"
    echo "   -> Your Pi is not connected to the internet."
    echo "   -> Check your WiFi or Ethernet cable."
    exit 1
fi

echo "\n[3] Checking DNS Resolution (Ping google.com)..."
ping -c 4 google.com
if [ $? -eq 0 ]; then
    echo "✅ DNS Resolution: OK"
else
    echo "❌ DNS Resolution: FAILED"
    echo "   -> Your Pi cannot translate domain names."
    echo "   -> Current /etc/resolv.conf content:"
    cat /etc/resolv.conf
fi

echo "\n[4] Checking System Time..."
current_date=$(date)
echo "   Current Time: $current_date"
echo "   (If this is wrong, SSL/HTTPS will fail)"

echo "\n========================================"
echo "Diagnostic Complete."
