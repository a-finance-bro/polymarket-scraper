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

echo "\n[2] Flushing Firewall Rules..."
# Try UFW (Uncomplicated Firewall)
sudo ufw disable 2>/dev/null
echo "UFW disabled (if present)."

# Try NFTables (Modern replacement for iptables)
sudo nft flush ruleset 2>/dev/null
echo "NFTables flushed (if present)."

# Try IPTables (Legacy)
sudo iptables -F 2>/dev/null
sudo iptables -X 2>/dev/null
sudo iptables -t nat -F 2>/dev/null
sudo iptables -t nat -X 2>/dev/null

echo "\n[3] Cleaning Routing Rules..."
# Check for VPN routing policies
sudo ip rule show
# Delete all rules except default (0, 32766, 32767)
# This is risky to script blindly, so let's just try to bring down the VPN interface
# If 10.2.0.2 exists, find its name
iface=$(ip -o addr show to 10.2.0.2 | awk '{print $2}')
if [ ! -z "$iface" ]; then
    echo "Killing VPN interface: $iface"
    sudo ip link set dev $iface down
    sudo ip addr del 10.2.0.2/32 dev $iface 2>/dev/null
fi

echo "\n[4] Disabling VPN Services (Permanent)..."
sudo systemctl disable wg-quick@wg0 2>/dev/null
sudo systemctl disable openvpn 2>/dev/null
sudo systemctl disable tailscaled 2>/dev/null

echo "\n[5] Testing Connection..."
echo "--- Pinging Gateway (192.168.68.1) ---"
ping -c 3 192.168.68.1

echo "\n--- Pinging Google (8.8.8.8) ---"
ping -c 3 8.8.8.8

echo "\n========================================"
echo "✅ Done. PLEASE REBOOT NOW!"
echo "Run: sudo reboot"

