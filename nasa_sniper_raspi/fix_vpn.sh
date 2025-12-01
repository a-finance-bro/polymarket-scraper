#!/bin/bash
echo "========================================"
echo "🧹 VPN Cleanup & Network Fix Tool"
echo "========================================"

echo "\n[1] Stopping common VPN services..."
# Try to stop WireGuard, OpenVPN, Tailscale
sudo systemctl stop wg-quick@wg0 2>/dev/null
sudo systemctl stop openvpn 2>/dev/null
sudo systemctl stop tailscaled 2>/dev/null
echo "Services stopped."

echo "\n[2] Flushing Firewall/IPTables Rules..."
# This removes "Killswitch" rules that block internet when VPN is off
sudo iptables -F
sudo iptables -X
sudo iptables -t nat -F
sudo iptables -t nat -X
sudo iptables -P INPUT ACCEPT
sudo iptables -P FORWARD ACCEPT
sudo iptables -P OUTPUT ACCEPT
echo "Firewall rules flushed."

echo "\n[3] Testing Connection..."
ping -c 3 8.8.8.8

echo "\n========================================"
echo "✅ Done. If the ping above worked, you are good!"
echo "If not, try rebooting: sudo reboot"
