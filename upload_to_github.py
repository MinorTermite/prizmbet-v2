#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Загрузка всех файлов PRIZMBET на GitHub
Запустить: python upload_to_github.py YOUR_TOKEN
"""
import sys, os, json, base64
from urllib.request import Request, urlopen
from urllib.error import HTTPError

# ========= КОНФИГ =========
GITHUB_OWNER = "MinorTermite"
GITHUB_REPO  = "betprizm"
BRANCH       = "main"

# Файлы для загрузки (из текущей папки скрипта)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

FILES_TO_UPLOAD = [
    "index.html",
    "matches.json",
    "netlify.toml",
    "auto_parser.py",
    "update_matches.py",
    "requirements.txt",
    "package.json",
    "README.md",
    "_redirects",
    ".gitignore",
    ".gitattributes",
]

GITHUB_WORKFLOW = ".github/workflows/update-matches.yml"

# ==========================

def gh_api(token, method, path, body=None):
    url = f"https://api.github.com{path}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
        "User-Agent": "PRIZMBET-Uploader/1.0"
    }
    data = json.dumps(body).encode() if body else None
    req = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode()), r.getcode()
    except HTTPError as e:
        err = e.read().decode()
        return json.loads(err) if err else {}, e.code

def get_file_sha(token, path):
    resp, code = gh_api(token, "GET", f"/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/{path}?ref={BRANCH}")
    if code == 200 and "sha" in resp:
        return resp["sha"]
    return None

def upload_file(token, filepath, content_bytes):
    sha = get_file_sha(token, filepath)
    encoded = base64.b64encode(content_bytes).decode()
    body = {
        "message": f"auto-update: {filepath}",
        "content": encoded,
        "branch": BRANCH
    }
    if sha:
        body["sha"] = sha
    resp, code = gh_api(token, "PUT", f"/repos/{GITHUB_OWNER}/{GITHUB_REPO}/contents/{filepath}", body)
    return code in (200, 201)

def main():
    if len(sys.argv) < 2:
        print("Usage: python upload_to_github.py GITHUB_TOKEN")
        print("Token needs: repo scope (write access)")
        sys.exit(1)

    token = sys.argv[1].strip()
    print(f"=== Uploading to github.com/{GITHUB_OWNER}/{GITHUB_REPO} ===\n")

    # Проверяем токен
    resp, code = gh_api(token, "GET", f"/repos/{GITHUB_OWNER}/{GITHUB_REPO}")
    if code != 200:
        print(f"ERROR: Cannot access repo (code {code}): {resp.get('message','')}")
        sys.exit(1)
    print(f"OK: Repo found: {resp.get('full_name')}\n")

    ok = 0
    fail = 0

    # Загружаем обычные файлы
    for filename in FILES_TO_UPLOAD:
        filepath = os.path.join(SCRIPT_DIR, filename)
        if not os.path.exists(filepath):
            print(f"  SKIP {filename} (not found)")
            continue
        try:
            with open(filepath, 'rb') as f:
                content = f.read()
            if upload_file(token, filename, content):
                print(f"  OK   {filename}")
                ok += 1
            else:
                print(f"  FAIL {filename}")
                fail += 1
        except Exception as e:
            print(f"  ERR  {filename}: {e}")
            fail += 1

    # Загружаем GitHub Actions workflow
    wf_path = os.path.join(SCRIPT_DIR, ".github", "workflows", "update-matches.yml")
    if os.path.exists(wf_path):
        with open(wf_path, 'rb') as f:
            content = f.read()
        if upload_file(token, GITHUB_WORKFLOW, content):
            print(f"  OK   {GITHUB_WORKFLOW}")
            ok += 1
        else:
            print(f"  FAIL {GITHUB_WORKFLOW}")
            fail += 1

    # Загружаем бинарные файлы (PNG, GIF, MP4)
    binary_files = ["prizmbet-info-1.png", "prizmbet-info-2.png", 
                    "prizmbet-logo.gif", "prizmbet-logo.mp4", "qr_wallet.png"]
    for filename in binary_files:
        filepath = os.path.join(SCRIPT_DIR, filename)
        if not os.path.exists(filepath):
            print(f"  SKIP {filename} (not found)")
            continue
        try:
            with open(filepath, 'rb') as f:
                content = f.read()
            if upload_file(token, filename, content):
                print(f"  OK   {filename}")
                ok += 1
            else:
                print(f"  FAIL {filename}")
                fail += 1
        except Exception as e:
            print(f"  ERR  {filename}: {e}")
            fail += 1

    print(f"\n=== DONE: {ok} uploaded, {fail} failed ===")
    if ok > 0:
        print(f"\nCheck: https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}")
        print(f"Site:  https://minortermite.github.io/betprizm/")

if __name__ == "__main__":
    main()
