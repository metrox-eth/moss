#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""POSIX USB CDC bench console; opens a port only when explicitly run by the operator.
No auto-rearm or reconnect. Drive commands are duration-limited. No third-party packages.
"""
import argparse,json,os,select,sys,termios,time

def drive_request(words):
    if len(words)!=4: raise ValueError('use: drive LEFT RIGHT MILLISECONDS')
    l,r,ms=map(int,words[1:])
    if not(-100<=l<=100 and -100<=r<=100 and 1<=ms<=5000):
        raise ValueError('percent -100..100, duration 1..5000ms')
    return f'drive {l} {r}',ms/1000

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('port');args=p.parse_args()
    fd=os.open(args.port,os.O_RDWR|os.O_NOCTTY|os.O_NONBLOCK)
    original=termios.tcgetattr(fd);raw=termios.tcgetattr(fd)
    raw[0]=raw[1]=raw[3]=0;raw[2]=termios.CLOCAL|termios.CREAD|termios.CS8
    raw[4]=raw[5]=termios.B115200;raw[6][termios.VMIN]=0;raw[6][termios.VTIME]=0
    termios.tcsetattr(fd,termios.TCSANOW,raw);termios.tcflush(fd,termios.TCIOFLUSH)
    pending=bytearray();incoming=bytearray();latest=None;latest_at=0
    lease=False;motion=None;deadline=0;last_send=0;known_generation=None
    def queue(line):
        if len(pending)>2048:raise RuntimeError('serial output stalled; exiting to expire firmware lease')
        pending.extend((line+'\n').encode('ascii'))
    queue('status')
    print('Prototype commissioning console. arm / stop / status / zero / ramp UP DOWN / servo ... / tone ...')
    print('Use drive LEFT RIGHT MILLISECONDS (1..5000 ms). Ctrl-D or Ctrl-C stops and exits.')
    try:
        while True:
            now=time.monotonic()
            if lease and now-latest_at>1.0:
                pending.clear();queue('stop');lease=False;motion=None
                print('Telemetry stale; session stopped. No automatic rearm.')
            if motion and now>=deadline:
                pending.clear();queue('stop');lease=False;motion=None
            if lease and now-last_send>=.1:
                queue(motion or 'keepalive');last_send=now
            readable,writable,_=select.select([fd,sys.stdin],[fd] if pending else [],[],.02)
            if fd in writable:
                n=os.write(fd,pending[:128]);del pending[:n]
            if fd in readable:
                data=os.read(fd,4096)
                if not data:raise RuntimeError('USB port disconnected')
                incoming.extend(data)
                if len(incoming)>8192:raise RuntimeError('invalid/unterminated device response')
                while b'\n' in incoming:
                    line,_,tail=incoming.partition(b'\n');incoming[:]=tail
                    text=line.decode('ascii',errors='replace').strip();print(text)
                    try: record=json.loads(text)
                    except ValueError:record={}
                    if 'arm_token' in record:
                        latest=record;latest_at=now
                        gen=record.get('generation')
                        if known_generation is not None and gen!=known_generation:
                            # Drop scheduled movement and all unsent commands on any device stop/fault.
                            lease=False;motion=None;pending.clear()
                        known_generation=gen
                    if text.startswith('ERR'):
                        lease=False;motion=None;pending.clear();queue('stop')
            if sys.stdin in readable:
                line=sys.stdin.readline()
                if not line:break
                line=line.strip();words=line.split()
                if not words:continue
                if words==['arm']:
                    if not latest or now-latest_at>.75 or latest.get('state')!=0:
                        print('Need recent stopped status; status requested. Type arm again after it arrives.');queue('status');continue
                    pending.clear();queue(f"arm {latest['arm_token']}");lease=True;last_send=now
                elif words[0]=='drive':
                    try:command,duration=drive_request(words)
                    except ValueError as exc:print(exc);continue
                    if not lease or not latest or latest.get('state') not in (5,6):
                        print('Wait for armed state 5 before drive.');continue
                    motion=command;deadline=now+duration;queue(command);last_send=now
                elif words==['stop']:
                    lease=False;motion=None;pending.clear();queue('stop')
                elif words[0]=='arm':print('Use arm without a manually cached token in this console.')
                else:queue(line)
    finally:
        # Best effort only; the firmware lease remains the fallback if USB is unavailable.
        try:os.write(fd,b'stop\n')
        except OSError:pass
        try:termios.tcsetattr(fd,termios.TCSANOW,original)
        except OSError:pass
        os.close(fd)

if __name__=='__main__':
    try:main()
    except (KeyboardInterrupt,EOFError):pass
    except (OSError,RuntimeError) as exc:sys.exit(str(exc))
