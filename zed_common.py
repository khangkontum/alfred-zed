import json
import os
import re
import sqlite3
import subprocess
import sys
from pathlib import Path


def settings_path():
    override = os.environ.get("ZED_SETTINGS_PATH")
    if override:
        return Path(override).expanduser()

    preferred = Path("~/.config/zed/settings.json").expanduser()
    if preferred.exists():
        return preferred

    fallback = Path("~/.zed/settings.json").expanduser()
    if fallback.exists():
        return fallback

    return preferred


def strip_json_comments(text):
    result = []
    in_string = False
    escaped = False
    i = 0

    while i < len(text):
        char = text[i]
        next_char = text[i + 1] if i + 1 < len(text) else ""

        if in_string:
            result.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            i += 1
            continue

        if char == '"':
            in_string = True
            result.append(char)
            i += 1
            continue

        if char == "/" and next_char == "/":
            i += 2
            while i < len(text) and text[i] not in "\r\n":
                i += 1
            continue

        if char == "/" and next_char == "*":
            i += 2
            while i + 1 < len(text) and not (text[i] == "*" and text[i + 1] == "/"):
                i += 1
            i += 2
            continue

        result.append(char)
        i += 1

    return "".join(result)


def strip_trailing_commas(text):
    result = []
    in_string = False
    escaped = False
    i = 0

    while i < len(text):
        char = text[i]

        if in_string:
            result.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            i += 1
            continue

        if char == '"':
            in_string = True
            result.append(char)
            i += 1
            continue

        if char == ",":
            j = i + 1
            while j < len(text) and text[j].isspace():
                j += 1
            if j < len(text) and text[j] in "}]":
                i += 1
                continue

        result.append(char)
        i += 1

    return "".join(result)


def load_settings():
    path = settings_path()
    if not path.exists():
        return {}, path

    text = path.read_text(encoding="utf-8")
    if not text.strip():
        return {}, path

    clean_text = strip_trailing_commas(strip_json_comments(text))
    return json.loads(clean_text), path


def save_settings(settings, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(settings, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def zed_data_dir():
    override = os.environ.get("ZED_DATA_DIR")
    if override:
        return Path(override).expanduser()

    if sys.platform == "darwin":
        return Path("~/Library/Application Support/Zed").expanduser()

    xdg_data_home = os.environ.get("XDG_DATA_HOME")
    if xdg_data_home:
        return Path(xdg_data_home).expanduser() / "zed"

    return Path("~/.local/share/zed").expanduser()


def zed_db_path():
    override = os.environ.get("ZED_DB_PATH")
    if override:
        return Path(override).expanduser()

    db_root = zed_data_dir() / "db"
    channel = os.environ.get("ZED_CHANNEL", "stable")
    preferred = db_root / f"0-{channel}" / "db.sqlite"
    if preferred.exists():
        return preferred

    for name in ("0-stable", "0-preview", "0-nightly", "0-dev"):
        candidate = db_root / name / "db.sqlite"
        if candidate.exists():
            return candidate

    return preferred


def load_recent_local_projects(limit=100):
    path = zed_db_path()
    if not path.exists():
        return [], path

    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        rows = connection.execute(
            """
            SELECT paths, timestamp
            FROM workspaces
            WHERE remote_connection_id IS NULL
              AND paths IS NOT NULL
              AND paths != ''
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    finally:
        connection.close()

    projects = []
    seen = set()
    for paths, timestamp in rows:
        for project_path in parse_workspace_paths(paths):
            if project_path in seen:
                continue
            seen.add(project_path)
            projects.append({"path": project_path, "timestamp": timestamp})

    return projects, path


def parse_workspace_paths(paths):
    if not paths:
        return []

    stripped = paths.strip()
    if stripped.startswith("["):
        try:
            values = json.loads(stripped)
            return [normalize_path(value) for value in values if value]
        except json.JSONDecodeError:
            pass

    return [normalize_path(value) for value in stripped.splitlines() if value.strip()]


def list_zed_windows():
    script = """
tell application "System Events"
  tell process "Zed"
    set windowNames to name of every window
  end tell
end tell
set output to ""
repeat with windowName in windowNames
  set output to output & windowName & linefeed
end repeat
return output
"""
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True,
        timeout=3,
    )
    if result.returncode != 0:
        message = (result.stderr or result.stdout).strip()
        raise RuntimeError(message or "Unable to read Zed windows")

    windows = []
    seen = set()
    for title in result.stdout.splitlines():
        title = title.strip()
        if not title or title in seen:
            continue
        seen.add(title)
        windows.append({"title": title})

    return windows


def focus_zed_window(title):
    script = """
on run argv
  set targetTitle to item 1 of argv
  tell application "Zed" to activate
  tell application "System Events"
    tell process "Zed"
      repeat with zedWindow in windows
        if name of zedWindow is targetTitle then
          perform action "AXRaise" of zedWindow
          return "focused"
        end if
      end repeat
    end tell
  end tell
  error "Zed window not found: " & targetTitle
end run
"""
    result = subprocess.run(
        ["osascript", "-e", script, title],
        capture_output=True,
        text=True,
        timeout=3,
    )
    if result.returncode != 0:
        message = (result.stderr or result.stdout).strip()
        raise RuntimeError(message or f"Unable to focus Zed window: {title}")


def find_matching_zed_window(path_or_url):
    target = normalize_path(path_or_url)
    project_name = target.rsplit("/", 1)[-1]
    if target.startswith("ssh://"):
        project_name = target.rstrip("/").rsplit("/", 1)[-1]

    if not project_name:
        return None

    try:
        windows = list_zed_windows()
    except Exception:
        return None

    lower_project = project_name.lower()
    for window in windows:
        if window["title"].lower() == lower_project:
            return window

    for window in windows:
        title = window["title"].lower()
        if title.startswith(f"{lower_project} ") or title.startswith(f"{lower_project} —"):
            return window

    return None


def connection_label(connection):
    nickname = connection.get("nickname")
    username = connection.get("username")
    host = connection.get("host", "")
    port = connection.get("port")

    target = host
    if username:
        target = f"{username}@{target}"
    if port:
        target = f"{target}:{port}"

    return f"{nickname} ({target})" if nickname else target


def zed_url(connection, path):
    username = connection.get("username")
    host = connection.get("host", "")
    port = connection.get("port")

    authority = host
    if username:
        authority = f"{username}@{authority}"
    if port:
        authority = f"{authority}:{port}"

    if path.startswith("/"):
        url_path = path
    else:
        url_path = "/" + path

    return f"ssh://{authority}{url_path}"


def normalize_path(path):
    path = (path or "~").strip()
    if path in {"", "~/"}:
        return "~"
    return re.sub(r"/+$", "", path)
