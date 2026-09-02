import os, pathlib, pytest
from app.tools.filesystem import read_project_file, write_project_file
from app.tools.permissions import ToolSecurityError

class TestSymlinkSecurity:
    def test_read_blocks_symlink_pointing_outside(self):
        link = pathlib.Path("tests/symlink_out")
        if link.exists(): link.unlink()
        os.symlink("/etc/passwd", str(link))
        try:
            with pytest.raises(ToolSecurityError):
                read_project_file("tests/symlink_out")
        finally:
            if link.exists() or link.is_symlink(): link.unlink()

    def test_write_blocks_symlink_pointing_outside(self):
        link = pathlib.Path("tests/symlink_out_w")
        if link.exists(): link.unlink()
        os.symlink("/tmp/outside.txt", str(link))
        try:
            with pytest.raises(ToolSecurityError):
                write_project_file("tests/symlink_out_w", "x")
        finally:
            if link.exists() or link.is_symlink(): link.unlink()

    def test_write_allows_internal_symlink(self):
        target = pathlib.Path("tests/symlink_target.txt")
        target.write_text("ok")
        link = pathlib.Path("tests/symlink_internal")
        if link.exists(): link.unlink()
        os.symlink("symlink_target.txt", str(link))
        try:
            write_project_file("tests/symlink_internal", "updated")
            assert target.read_text() == "updated"
        finally:
            if link.exists() or link.is_symlink(): link.unlink()
            target.unlink(missing_ok=True)
