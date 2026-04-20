#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

python3 start_server.py
STATUS=$?

if [ $STATUS -ne 0 ]; then
  echo
  read -r -p "启动失败，按回车键退出..." _
fi
