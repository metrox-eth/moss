#!/bin/bash
# Start the servo watcher in the background (kill any previous one by pidfile, never by pattern).
cd ~/moss_fw_v04
[ -f watch.pid ] && kill "$(cat watch.pid)" 2>/dev/null
rm -f watch.log
nohup ~/vector-dimos/.venv/bin/python servo_watch.py watch.log "$@" >watch.err 2>&1 &
echo $! > watch.pid
sleep 2; cat watch.log; echo "pid $(cat watch.pid) alive: $(kill -0 $(cat watch.pid) 2>/dev/null && echo yes || echo no)"
