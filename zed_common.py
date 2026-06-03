import json
import os
import re
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
