#!/usr/bin/env python3
import json
import subprocess
import sys

sys.dont_write_bytecode = True

from zed_common import (
    connection_label,
    find_matching_zed_window,
    focus_zed_window,
    list_zed_windows,
    load_recent_local_projects,
    load_settings,
    normalize_path,
    settings_path,
    zed_url,
)


def matches(query, *parts):
    tokens = query.lower().split()
    haystack = " ".join(part for part in parts if part).lower()
    return all(token in haystack for token in tokens)


def iter_projects(settings):
    for connection in settings.get("ssh_connections", []):
        for project in connection.get("projects", []):
            for path in project.get("paths", []):
                yield connection, normalize_path(path)


def remote_script_filter(query):
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


def local_script_filter(query):
    try:
        projects, path = load_recent_local_projects()
    except Exception as error:
        print(json.dumps({"items": [{
            "title": "Could not read Zed recent projects",
            "subtitle": str(error),
            "valid": False,
        }]}))
        return

    items = []
    for project in projects:
        project_path = project["path"]
        title = project_path.rsplit("/", 1)[-1] or project_path
        if query and not matches(query, title, project_path):
            continue

        items.append({
            "title": title,
            "subtitle": f"Open {project_path} in Zed",
            "arg": project_path,
            "autocomplete": title,
            "valid": True,
        })

    if not items:
        items.append({
            "title": "No Zed recent local projects found",
            "subtitle": f"Recent projects database: {path}",
            "valid": False,
        })

    print(json.dumps({"items": items}, ensure_ascii=False))


def windows_script_filter(query):
    try:
        windows = list_zed_windows()
    except Exception as error:
        print(json.dumps({"items": [{
            "title": "Could not read Zed windows",
            "subtitle": f"{error}. Grant Alfred Accessibility permission in macOS Settings.",
            "valid": False,
        }]}))
        return

    items = []
    for window in windows:
        title = window["title"]
        display_title = window.get("display_title", title)
        if query and not matches(query, title, display_title):
            continue

        items.append({
            "title": display_title,
            "subtitle": "Focus open Zed window",
            "arg": f"window:{title}",
            "autocomplete": display_title,
            "valid": True,
        })

    if not items:
        items.append({
            "title": "No open Zed windows found",
            "subtitle": "Open a Zed project first, or grant Alfred Accessibility permission.",
            "valid": False,
        })

    print(json.dumps({"items": items}, ensure_ascii=False))


def open_in_zed(target):
    if target.startswith("-"):
        raise SystemExit(f"Refusing to open option-like path: {target}")

    if target.startswith("window:"):
        title = target.removeprefix("window:")
        focus_zed_window(title)
        print(title)
        return

    window = find_matching_zed_window(target)
    if window:
        focus_zed_window(window["title"])
        print(window["title"])
        return

    subprocess.Popen(["zed", target], start_new_session=True)
    print(target)


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "filter"
    query = sys.argv[2] if len(sys.argv) > 2 else ""

    if mode == "open":
        open_in_zed(query)
    elif mode == "windows":
        windows_script_filter(query)
    elif mode == "remote":
        if not settings_path().exists():
            pass
        remote_script_filter(query)
    else:
        local_script_filter(query)


if __name__ == "__main__":
    main()
