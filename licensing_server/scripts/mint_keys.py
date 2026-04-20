import argparse
import random
import sqlite3
import string
import time
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / 'licenses.db'

ALPHABET = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'  # no I, O, 0, 1

def gen_key(blocks=4, block_size=4):
    return '-'.join(''.join(random.choice(ALPHABET) for _ in range(block_size)) for _ in range(blocks))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--count', type=int, default=1)
    ap.add_argument('--plan', type=str, default='pro')
    ap.add_argument('--max-devices', type=int, default=1)
    args = ap.parse_args()

    conn = sqlite3.connect(DB_PATH)
    conn.execute('create table if not exists licenses (license_key text primary key, plan text, max_devices integer, active integer, issued_at integer, notes text)')
    now = int(time.time())
    keys = []
    for _ in range(args.count):
        key = gen_key()
        keys.append(key)
        conn.execute('insert or replace into licenses (license_key, plan, max_devices, active, issued_at, notes) values (?,?,?,?,?,?)',
                     (key, args.plan, args.max_devices, 1, now, None))
    conn.commit()
    print('Generated keys:')
    for k in keys:
        print(' ', k)

if __name__ == '__main__':
    main()

