#!/usr/bin/env python3
import json
import shlex
import sys

sys.dont_write_bytecode = True

from zed_common import load_settings, normalize_path, save_settings


def parse_ssh_target(command):
    parts = shlex.split(command)
    if parts and parts[0] == "ssh":
        parts = parts[1:]

    username = None
    host = None
    port = None
    leftovers = []
    i = 0

    while i < len(parts):
        part = parts[i]
        if part == "-l" and i + 1 < len(parts):
            username = parts[i + 1]
            i += 2
        elif part == "-p" and i + 1 < len(parts):
            port = int(parts[i + 1])
            i += 2
        elif part.startswith("-"):
            if part in {"-i", "-o", "-J", "-F", "-b", "-c", "-D", "-I", "-L", "-m", "-R", "-w"} and i + 1 < len(parts):
                i += 2
            else:
                i += 1
        elif host is None:
            host = part
            i += 1
        else:
            leftovers.append(part)
            i += 1

    if not host:
        raise ValueError("Usage: !za ssh user@host[:port] /path")

    if "@" in host:
        username, host = host.rsplit("@", 1)

    if ":" in host and not host.startswith("["):
        possible_host, possible_port = host.rsplit(":", 1)
        if possible_port.isdigit():
            host = possible_host
            port = int(possible_port)

    path = normalize_path(leftovers[0] if leftovers else "~")
    return username, host, port, path


def add_target(command):
    username, host, port, project_path = parse_ssh_target(command)
    settings, path = load_settings()
    connections = settings.setdefault("ssh_connections", [])

    connection = None
    for candidate in connections:
        if (
            candidate.get("host") == host
            and candidate.get("username") == username
            and candidate.get("port") == port
        ):
            connection = candidate
            break

    if connection is None:
        connection = {"host": host, "projects": []}
        if username:
            connection["username"] = username
        if port:
            connection["port"] = port
        connections.append(connection)

    projects = connection.setdefault("projects", [])
    for project in projects:
        paths = project.setdefault("paths", [])
        if project_path in paths:
            return f"Already exists: {host} {project_path}"

    projects.append({"paths": [project_path]})
    save_settings(settings, path)
    return f"Added: {host} {project_path}"


def main():
    command = sys.argv[1] if len(sys.argv) > 1 else ""
    try:
        message = add_target(command)
    except Exception as error:
        message = f"Failed: {error}"
        print(json.dumps({"alfredworkflow": {"arg": message}}))
        raise SystemExit(1)

    print(json.dumps({"alfredworkflow": {"arg": message}}))


if __name__ == "__main__":
    main()
