#!/bin/bash

ps aux | grep 'python' |grep "main.py"  
ps aux | grep 'python' |grep "main.py" | awk '{print $2}' | xargs -r kill -9

ps aux | grep 'python' |grep "spb_server.py"  
ps aux | grep 'python' |grep "spb_server.py" | awk '{print $2}' | xargs -r kill -9

ps aux | grep 'python' |grep "biz_app.py"  
ps aux | grep 'python' |grep "biz_app.py" | awk '{print $2}' | xargs -r kill -9
