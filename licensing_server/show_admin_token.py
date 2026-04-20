import os
from pathlib import Path
import re
import uuid
import webbrowser
import tkinter as tk
from tkinter import messagebox

def read_token():
    token = (os.environ.get('ADMIN_TOKEN') or '').strip()
    if token:
        return token

    token_file = (os.environ.get('ADMIN_TOKEN_FILE') or '').strip()
    if token_file:
        tf = Path(token_file)
        if tf.exists():
            raw = tf.read_text(encoding='utf-8').strip()
            if raw:
                return raw

    # Fallback for local debugging only (not persisted to disk).
    return uuid.uuid4().hex

def main():
    token = read_token()
    port = os.environ.get('PORT', '8787')

    root = tk.Tk()
    root.title('Vox Stella — Admin Token')
    root.geometry('520x200')

    def copy():
        root.clipboard_clear()
        root.clipboard_append(token)
        messagebox.showinfo('Copied', 'Admin token copied to clipboard.')

    def open_login():
        url = f'http://127.0.0.1:{port}/admin/login'
        webbrowser.open(url)

    tk.Label(root, text='Admin Token', font=('Segoe UI', 11, 'bold')).pack(pady=(16, 8))
    entry = tk.Entry(root, width=50, font=('Consolas', 11))
    entry.insert(0, token)
    entry.configure(state='readonly')
    entry.pack(pady=4)

    btn_frame = tk.Frame(root)
    btn_frame.pack(pady=12)
    tk.Button(btn_frame, text='Copy Token', command=copy, width=14).pack(side=tk.LEFT, padx=6)
    tk.Button(btn_frame, text='Open Admin Login', command=open_login, width=18).pack(side=tk.LEFT, padx=6)
    tk.Button(btn_frame, text='Close', command=root.destroy, width=10).pack(side=tk.LEFT, padx=6)

    tk.Label(root, text='Paste this token on the Admin Login page to access the dashboard.', fg='#666').pack()
    root.mainloop()

if __name__ == '__main__':
    main()
