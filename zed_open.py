#!/usr/bin/env python3
import json
import subprocess
import sys

sys.dont_write_bytecode = True

from zed_common import connection_label, load_settings, normalize_path, settings_path, zed_url


def matches(query, *parts):
    tokens = query.lower().split()
    haystack = " ".join(part for part in parts if part).lower()
    return all(token in haystack for token in tokens)


def iter_projects(settings):
    for connection in settings.get("ssh_connections", []):
        for project in connection.get("projects", []):
            for path in project.get("paths", []):
                yield connection, normalize_path(path)


def script_filter(query):
    try:
        settings, path = load_settings()
    except Exception as error:
        print(json.dumps({"items": [{
            "title": "Could not read Zed settings",
            "subtitle": str(error),
            "valid": False,
        }]}))
        return

    items = []
    for connection, path_value in iter_projects(settings):
        label = connection_label(connection)
        url = zed_url(connection, path_value)
        if query and not matches(query, label, path_value, url):
            continue

        items.append({
            "title": f"{label}  {path_value}",
            "subtitle": f"Open {url} in Zed",
            "arg": url,
            "autocomplete": f"{label} {path_value}",
            "valid": True,
        })

    if not items:
        add_hint = "!za ssh user@host /absolute/path"
        items.append({
            "title": "No Zed SSH projects found",
            "subtitle": f"Add one with {add_hint}. Settings: {path}",
            "valid": False,
        })

    print(json.dumps({"items": items}, ensure_ascii=False))


def open_in_zed(url):
    if not url.startswith("ssh://"):
        raise SystemExit(f"Refusing to open non-SSH URL: {url}")
    subprocess.Popen(["zed", url], start_new_session=True)
    print(url)


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "filter"
    query = sys.argv[2] if len(sys.argv) > 2 else ""

    if mode == "open":
        open_in_zed(query)
    else:
        if not settings_path().exists():
            pass
        script_filter(query)


if __name__ == "__main__":
    main()
