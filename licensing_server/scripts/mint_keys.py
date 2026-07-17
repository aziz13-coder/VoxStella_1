import argparse
import secrets
import sqlite3
import time
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / 'licenses.db'

ALPHABET = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'  # no I, O, 0, 1

def gen_key(blocks=4, block_size=4):
    return '-'.join(''.join(secrets.choice(ALPHABET) for _ in range(block_size)) for _ in range(blocks))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--count', type=int, default=1)
    ap.add_argument('--plan', type=str, default='pro')
    ap.add_argument('--max-devices', type=int, default=1)
    args = ap.parse_args()
    if args.count <= 0:
        ap.error('--count must be positive')
    if args.max_devices <= 0:
        ap.error('--max-devices must be positive')

    conn = sqlite3.connect(DB_PATH)
    conn.execute('create table if not exists licenses (license_key text primary key, plan text, max_devices integer, active integer, issued_at integer, notes text)')
    now = int(time.time())
    keys = []
    for _ in range(args.count):
        for _attempt in range(100):
            key = gen_key()
            try:
                conn.execute(
                    'insert into licenses (license_key, plan, max_devices, active, issued_at, notes) values (?,?,?,?,?,?)',
                    (key, args.plan, args.max_devices, 1, now, None),
                )
                keys.append(key)
                break
            except sqlite3.IntegrityError:
                continue
        else:
            raise RuntimeError('Could not generate a unique license key')
    conn.commit()
    print('Generated keys:')
    for k in keys:
        print(' ', k)

if __name__ == '__main__':
    main()
