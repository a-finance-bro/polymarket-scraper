# NASA Sniper (Raspberry Pi Edition) 🥧

This folder contains a robust, 24/7 version of the NASA Sniper designed to run on a Raspberry Pi.

## Prerequisites
-   Raspberry Pi 4 (or similar) with Raspbian/Debian.
-   Internet connection.
-   Monitor connected (for status output).

## Setup Instructions

### 1. SSH into your Pi
Find your Pi's IP address and SSH in:
```bash
ssh pi@<YOUR_PI_IP>
```

### 2. Transfer Files
You can copy this entire folder to your Pi using `scp` from your main computer:
```bash
scp -r nasa_sniper_raspi pi@<YOUR_PI_IP>:~/nasa_sniper
```
*Or just git clone the repo if you have git set up.*

### 3. Install Dependencies (On Pi)
**Important**: Modern Raspberry Pi OS requires a virtual environment to install Python packages.

1.  **Remove old version (if exists)**:
    ```bash
    rm -rf nasa_sniper_raspi
    ```

2.  **Transfer new code (From your Computer)**:
    ```bash
    scp -r nasa_sniper_raspi jjcam@<YOUR_PI_IP>:~/
    ```

3.  **SSH into Pi**:
    ```bash
    ssh jjcam@<YOUR_PI_IP>
    cd nasa_sniper_raspi
    ```

4.  **Create & Activate Virtual Environment**:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

5.  **Install Dependencies**:
    ```bash
    pip3 install requests python-dotenv py-clob-client
    ```

### 4. Configuration
1.  **Generate Token Map**:
    ```bash
    python3 fetch_tokens.py
    ```
    *Ensure `token_map.json` is created.*

2.  **Set Private Key**:
    Create a `.env` file:
    ```bash
    nano .env
    ```
    Paste your key:
    ```
    PRIVATE_KEY=0xYOUR_PRIVATE_KEY_HERE
    ```
    Save (Ctrl+O, Enter) and Exit (Ctrl+X).

## Troubleshooting

### Network / Pip Errors ("Connection Broken", "Temporary Failure")
This is a **DNS Resolution Error**. Your Pi cannot translate "pypi.org" to an IP address.

**Step 1: Check if you have Internet**
Ping Google's IP directly (bypasses DNS):
```bash
ping -c 4 8.8.8.8
```
*   If this **fails** (100% packet loss), your Pi is **offline**. Check your WiFi/Ethernet cable.
*   If this **works**, you have internet but **bad DNS**. Proceed to Step 2.

**Step 2: Force Google DNS**
Overwrite your DNS settings temporarily to force it to work:
```bash
sudo sh -c 'echo "nameserver 8.8.8.8" > /etc/resolv.conf'
```

**Step 3: Retry Install**
```bash
pip3 install requests python-dotenv py-clob-client
```

3.  **Fix System Time** (SSL fails if time is wrong):
    ```bash
    sudo date -s "$(wget -qSO- --max-redirect=0 google.com 2>&1 | grep Date: | cut -d' ' -f5-8)Z"
    ```

### "Externally Managed Environment"
Ensure you are using the virtual environment:
```bash
source venv/bin/activate
```

### Features
-   **Status Report**: Prints status every 5 seconds (e.g., `[12:00:05] Status: Monitoring... | Nov Value: ****`).
-   **Robustness**: Handles network errors gracefully and retries.
-   **Instant Execution**: Places buy order immediately when value changes.
-   **Visual Alert**: Prints a large alert message upon success.

### Keep Alive (Optional)
If you want to detach but keep it running (e.g. if you SSH out), use `tmux`:
```bash
sudo apt install tmux -y
tmux new -s sniper
python3 sniper_pi.py
# Detach with Ctrl+B, then D
# Reattach with: tmux attach -t sniper
```
