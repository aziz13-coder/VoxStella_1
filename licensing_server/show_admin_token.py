import os
from pathlib import Path

TOKEN_RELATIVE_PATH = Path("VoxStella") / "licensing" / "admin_token.txt"


def default_token_file(environ=None):
    env = os.environ if environ is None else environ
    local_app_data = (env.get("LOCALAPPDATA") or "").strip()
    if not local_app_data:
        return None
    return Path(local_app_data) / TOKEN_RELATIVE_PATH


def read_token(environ=None):
    env = os.environ if environ is None else environ
    token = (env.get('ADMIN_TOKEN') or '').strip()
    if token:
        return token

    candidates = []
    explicit_token_file = (env.get('ADMIN_TOKEN_FILE') or '').strip()
    if explicit_token_file:
        candidates.append(Path(explicit_token_file))
    canonical_token_file = default_token_file(env)
    if canonical_token_file is not None and canonical_token_file not in candidates:
        candidates.append(canonical_token_file)

    for tf in candidates:
        if tf.exists():
            try:
                raw = tf.read_text(encoding='utf-8').strip()
            except OSError:
                continue
            if raw:
                return raw

    raise RuntimeError(
        "The admin token is not configured. Start run-licensing-server.bat "
        "or set ADMIN_TOKEN/ADMIN_TOKEN_FILE to the server's existing token."
    )

def main():
    import tkinter as tk
    import webbrowser
    from tkinter import messagebox

    try:
        token = read_token()
    except RuntimeError as exc:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror('Admin token unavailable', str(exc))
        root.destroy()
        return 1

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
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
