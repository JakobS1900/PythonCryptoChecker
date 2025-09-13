#!/usr/bin/env python3
import sys
import os
import re

ROOT = os.path.dirname(os.path.dirname(__file__))

EXCLUDE_DIRS = {'.git', '.venv', 'venv', 'env', '__pycache__', 'node_modules', 'logs'}
EXCLUDE_EXT = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.ico', '.db', '.sqlite', '.sqlite3', '.woff', '.woff2', '.ttf', '.eot', '.pdf'}

def should_skip(path: str) -> bool:
    parts = path.split(os.sep)
    if any(p in EXCLUDE_DIRS for p in parts):
        return True
    _, ext = os.path.splitext(path)
    if ext.lower() in EXCLUDE_EXT:
        return True
    return False

def load_words():
    words_path = os.path.join(ROOT, '.prohibited_words.txt')
    with open(words_path, 'r', encoding='utf-8') as f:
        words = [w.strip() for w in f if w.strip() and not w.startswith('#')]
    # Compile regex to match whole words case-insensitively
    patterns = [re.compile(rf"\b{re.escape(w)}\b", re.IGNORECASE) for w in words]
    return words, patterns

def scan():
    words, patterns = load_words()
    failures = []
    for root, dirs, files in os.walk(ROOT):
        # prune excluded dirs
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for fname in files:
            path = os.path.join(root, fname)
            if should_skip(path):
                continue
            try:
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    for i, line in enumerate(f, 1):
                        for pat in patterns:
                            if pat.search(line):
                                failures.append((path, i, line.rstrip()))
                                break
            except Exception:
                # skip unreadable files
                continue
    if failures:
        print('Prohibited words found:')
        for path, ln, text in failures:
            print(f"  {path}:{ln}: {text}")
        print('\nTo update the list, edit .prohibited_words.txt')
        return 1
    else:
        print('No prohibited words detected.')
        return 0

if __name__ == '__main__':
    sys.exit(scan())

