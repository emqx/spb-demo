#!/bin/sh

cd /root/spb-demo

nohup uv run spb_server.py &
nohup uv run biz_app.py &

exec uv run main.py

