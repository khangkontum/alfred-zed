# Alfred Zed

Alfred workflow for opening Zed projects.

- `!zo` lists and filters recent local projects from Zed's SQLite database.
- `!zor` lists and filters remote projects from Zed `ssh_connections`.
- `!zow` lists and focuses currently open Zed windows.
- `!za ssh user@example.com /home/user/project` adds a remote project to Zed settings.

Selecting a project focuses a matching open Zed window when possible, otherwise it runs `zed <path>` or `zed ssh://user@example.com/home/user/project`.
