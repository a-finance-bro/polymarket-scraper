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

echo "\n[3] Testing Connection..."
echo "--- Pinging Gateway (192.168.68.1) ---"
ping -c 3 192.168.68.1

echo "\n--- Pinging Google (8.8.8.8) ---"
ping -c 3 8.8.8.8

echo "\n========================================"
echo "✅ Done. If the ping above worked, you are good!"
echo "If not, try rebooting: sudo reboot"
