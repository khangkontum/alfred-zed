# Alfred Zed

Alfred workflow for opening Zed projects.

- `!zo` lists and filters recent local projects from Zed's SQLite database.
- `!zor` lists and filters remote projects from Zed `ssh_connections`.
- `!za ssh user@example.com /home/user/project` adds a remote project to Zed settings.

Selecting a result runs `zed <path>` or `zed ssh://user@example.com/home/user/project`.
