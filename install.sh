#!/bin/bash

set -e

echo "[*] Updating system packages..."
sudo apt update -y
sudo apt upgrade -y

echo "[*] Installing required system packages..."
sudo apt install -y python3 python3-pip nodejs npm curl

echo "[*] Installing Python packages (with break-system-packages)..."
pip3 install --break-system-packages requests flask

# Install servor globally using npm if not installed
if ! command -v servor &> /dev/null
then
    echo "[*] Installing servor via npm..."
    sudo npm install -g servor
else
    echo "[*] servor already installed."
fi

# Install ngrok if not installed
if ! command -v ngrok &> /dev/null
then
    echo "[*] Installing ngrok..."
    NGROK_URL="https://bin.equinox.io/c/4VmDzA7iaHb/ngrok-stable-linux-amd64.zip"
    TMP_DIR=$(mktemp -d)
    curl -sL $NGROK_URL -o "$TMP_DIR/ngrok.zip"
    unzip -q "$TMP_DIR/ngrok.zip" -d "$TMP_DIR"
    sudo mv "$TMP_DIR/ngrok" /usr/local/bin/ngrok
    sudo chmod +x /usr/local/bin/ngrok
    rm -rf "$TMP_DIR"
else
    echo "[*] ngrok already installed."
fi

# Install cloudflared if not installed
if ! command -v cloudflared &> /dev/null
then
    echo "[*] Installing cloudflared..."
    CLOUDFLARED_URL="https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64"
    sudo curl -sLo /usr/local/bin/cloudflared $CLOUDFLARED_URL
    sudo chmod +x /usr/local/bin/cloudflared
else
    echo "[*] cloudflared already installed."
fi

echo "[*] Installation complete! Please restart your terminal or run 'source ~/.bashrc' if you installed ngrok."


