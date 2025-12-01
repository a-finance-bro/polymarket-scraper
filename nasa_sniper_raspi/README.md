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
Update apt and install Python 3 & pip:
```bash
sudo apt update
sudo apt install python3 python3-pip -y
```

Install required Python libraries:
```bash
pip3 install requests python-dotenv py-clob-client
```
*Note: If `py-clob-client` fails to build, you might need build tools:*
```bash
sudo apt install build-essential libgmp-dev python3-dev -y
```

### 4. Configuration
1.  **Generate Token Map**:
    Run the fetch script to get the latest Token IDs.
    ```bash
    python3 fetch_tokens.py
    ```
    *Ensure `token_map.json` is created.*

2.  **Set Private Key**:
    Create a `.env` file in the folder:
    ```bash
    nano .env
    ```
    Paste your key:
    ```
    PRIVATE_KEY=0xYOUR_PRIVATE_KEY_HERE
    ```
    Save (Ctrl+O, Enter) and Exit (Ctrl+X).

## Running the Sniper 🚀

To run it non-stop and see the status on your monitor:

```bash
python3 sniper_pi.py
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
