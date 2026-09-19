"""Write validated source TEXT into a fresh private staging directory, never execute.

Used by the certified multi-module runners after their isolation pilots.
The caller owns the temporary directory and cleanup, on the Linux workspace.
"""
import os
from pathlib import Path

from app.services.multifile_profile import require_sources


def stage_sources(folder: Path, files: dict[str, str]) -> None:
    require_sources(files)  # Validate everything before writing anything.
    if any(parent.is_symlink() for parent in (folder, *folder.parents)):
        raise ValueError('Staging nie może zawierać dowiązań.')
    stat = folder.stat()
    if not folder.is_dir() or stat.st_uid != os.geteuid() or stat.st_mode & 0o077 or any(folder.iterdir()):
        raise ValueError('Wymagany nowy, pusty, prywatny katalog stagingu.')
    # Fresh directory remains 0700 until all files have been written. No archive
    # extraction, external source paths, symlinks, executable bits or overwrite.
    directories = {folder}
    for path, content in sorted(files.items()):
        target = folder / path
        target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        with target.open('x', encoding='utf-8', newline='') as stream:
            stream.write(content)
        target.chmod(0o444)
        directories.update(target.parents)
    for directory in sorted((p for p in directories if p != folder and folder in p.parents), key=lambda p: len(p.parts), reverse=True):
        directory.chmod(0o755)
    folder.chmod(0o755)
