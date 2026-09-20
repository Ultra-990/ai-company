"""Linux-only, bounded source export. No archive extraction or code execution."""
from contextlib import contextmanager
from hashlib import sha256
import fcntl
import os
from pathlib import Path
import stat

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.artifact import Artifact, ArtifactType
from app.models.audit import AuditEvent
from app.services.workspace_packages import canonical_json, read_package, PackageIntegrityError
from app.services.media_packages import bytes_of

EXPORT_NAME = "organization-os.disk-export.v1"
MARKER = ".export.json"
ROOT = Path("/home/marcin/ai-company-workspaces")
MIN_FREE_BYTES = 10 * 1024**3
MAX_EXPORTS = 500
DIRECTORY_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC


class StorageUnavailable(RuntimeError):
    pass


class ExportConflict(RuntimeError):
    pass


class ExportMissing(LookupError):
    pass


class WorkspaceStorage:
    def __init__(self, root=ROOT, device_reference=Path("/home"), min_free_bytes=MIN_FREE_BYTES):
        # Server-controlled only; no API input may set any of these parameters.
        self.root = Path(root)
        self.device_reference = Path(device_reference)
        self.min_free_bytes = min_free_bytes

    @contextmanager
    def directory(self):
        """Open every ancestor without symlinks. Pin the permitted filesystem."""
        if not self.root.is_absolute() or ".." in self.root.parts:
            raise StorageUnavailable("Nieprawidłowy katalog magazynu.")
        fd = os.open("/", DIRECTORY_FLAGS)
        try:
            for part in self.root.parts[1:]:
                next_fd = os.open(part, DIRECTORY_FLAGS, dir_fd=fd)
                os.close(fd)
                fd = next_fd
            expected_device = os.stat(self.device_reference).st_dev
            self._private_directory(fd, expected_device)
            next_fd = os.open("packages", DIRECTORY_FLAGS, dir_fd=fd)
            os.close(fd)
            fd = next_fd
            self._private_directory(fd, expected_device)
            yield fd
        except OSError as exc:
            raise StorageUnavailable("Magazyn niedostępny lub ścieżka została podmieniona. Nie zmieniono montowania.") from exc
        finally:
            os.close(fd)

    @staticmethod
    def _private_directory(fd, device):
        s = os.fstat(fd)
        if s.st_dev != device or s.st_uid != os.geteuid() or stat.S_IMODE(s.st_mode) & 0o077:
            raise StorageUnavailable("Magazyn wymaga właściwej partycji, właściciela i prywatnych uprawnień 0700.")

    @staticmethod
    def _available(fd):
        s = os.fstatvfs(fd)
        return s.f_bavail * s.f_frsize

    def status(self):
        with self.directory() as fd:
            count = len(os.listdir(fd))
            available = self._available(fd)
        return dict(root=str(self.root / "packages"), available_bytes=available,
                    reserve_bytes=self.min_free_bytes, entries=count, max_exports=MAX_EXPORTS,
                    execution_enabled=False, hard_quota=False)

    @staticmethod
    def identity(task_id, package_id, checksum, payload):
        name = f"task-{task_id}-package-{package_id}-{checksum}"
        manifest = dict(schema=EXPORT_NAME, task_id=task_id, package_id=package_id,
                        source_checksum=checksum,
                        files=[{k: v for k, v in f.items() if k != "content"} for f in payload["files"]])
        return name, canonical_json(manifest).encode()

    @staticmethod
    def _write(fd, name, raw):
        output = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600, dir_fd=fd)
        with os.fdopen(output, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())

    @staticmethod
    def _read(fd, name, expected_size, expected_device):
        source = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC, dir_fd=fd)
        with os.fdopen(source, "rb") as stream:
            s = os.fstat(stream.fileno())
            if (not stat.S_ISREG(s.st_mode) or s.st_nlink != 1 or s.st_dev != expected_device
                    or s.st_size != expected_size):
                raise ExportConflict("Zapis zawiera zmieniony plik, dowiązanie lub niewłaściwy typ pliku.")
            return stream.read(expected_size + 1)

    def _verify(self, folder, payload, marker):
        device = os.fstat(folder).st_dev
        if self._read(folder, MARKER, len(marker), device) != marker:
            raise ExportConflict("Brak poprawnego znacznika zakończonego eksportu.")
        expected = {"": {MARKER}}
        for entry in payload["files"]:
            parts = entry["path"].split("/")
            for i, part in enumerate(parts):
                expected.setdefault("/".join(parts[:i]), set()).add(part)
        # Traverse only the bounded, validated manifest, never arbitrary disk trees.
        for directory, names in expected.items():
            fd = os.dup(folder)
            try:
                if directory:
                    for part in directory.split("/"):
                        next_fd = os.open(part, DIRECTORY_FLAGS, dir_fd=fd)
                        os.close(fd); fd = next_fd
                        if os.fstat(fd).st_dev != device: raise ExportConflict("Zmieniono urządzenie katalogu eksportu.")
                if set(os.listdir(fd)) != names:
                    raise ExportConflict("Eksport jest niepełny albo zawiera dodatkowe pliki. Nie nadpisano danych.")
            finally: os.close(fd)
        for entry in payload["files"]:
            fd = os.dup(folder)
            try:
                parts = entry["path"].split("/")
                for part in parts[:-1]:
                    next_fd = os.open(part, DIRECTORY_FLAGS, dir_fd=fd)
                    os.close(fd); fd = next_fd
                raw = self._read(fd, parts[-1], entry["size_bytes"], device)
                if sha256(raw).hexdigest() != entry["sha256"]:
                    raise ExportConflict("Treść eksportu różni się od paczki. Nie nadpisano danych.")
            finally: os.close(fd)

    def export(self, task_id, package_id, checksum, payload, *, create=True):
        name, marker = self.identity(task_id, package_id, checksum, payload)
        with self.directory() as root:
            try:
                fcntl.flock(root, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise StorageUnavailable("Inna operacja magazynu trwa. Ponów za chwilę.") from exc
            created = False
            try:
                os.stat(name, dir_fd=root, follow_symlinks=False)
            except FileNotFoundError:
                if not create: raise ExportMissing("Ta paczka nie ma jeszcze eksportu na dysku.")
                if len(os.listdir(root)) >= MAX_EXPORTS:
                    raise StorageUnavailable("Osiągnięto limit 500 wpisów magazynu. Wymagana decyzja o archiwizacji.")
                # Advisory reserve, not an OS quota; metadata allocation also needs room.
                needed = self.min_free_bytes + 64 * 1024**2 + sum(f["size_bytes"] for f in payload["files"])
                if self._available(root) < needed:
                    raise StorageUnavailable("Za mało wolnego miejsca z zachowaniem rezerwy. Nie zapisano paczki.")
                try:
                    os.mkdir(name, 0o700, dir_fd=root)
                    created = True
                    os.fsync(root)
                except FileExistsError:
                    pass  # Concurrent owner request: validate, never overwrite.
            folder = None
            try:
                folder = os.open(name, DIRECTORY_FLAGS, dir_fd=root)
                self._private_directory(folder, os.fstat(root).st_dev)
                if created:
                    for entry in payload["files"]:
                        fd = os.dup(folder)
                        try:
                            parts = entry["path"].split("/")
                            for part in parts[:-1]:
                                try:
                                    os.mkdir(part, 0o700, dir_fd=fd)
                                    os.fsync(fd)
                                except FileExistsError: pass
                                next_fd = os.open(part, DIRECTORY_FLAGS, dir_fd=fd)
                                os.close(fd); fd = next_fd
                                self._private_directory(fd, os.fstat(folder).st_dev)
                            self._write(fd, parts[-1], bytes_of(entry))
                            os.fsync(fd)
                        finally: os.close(fd)
                    self._write(folder, MARKER, marker)  # Commit marker is always last.
                    os.fsync(folder)
                self._verify(folder, payload, marker)
            except OSError as exc:
                raise ExportConflict("Niepełny lub zmieniony zapis na dysku. Pozostawiono go bez usuwania i nadpisywania.") from exc
            finally:
                if folder is not None: os.close(folder)
        return dict(task_id=task_id, package_id=package_id, source_checksum=checksum,
                    directory=str(self.root / "packages" / name), file_count=len(payload["files"]),
                    total_bytes=sum(f["size_bytes"] for f in payload["files"]),
                    verified=True, code_executed=False, created=created)


def export_package(session: Session, storage: WorkspaceStorage, task_id: int, package_id: int, *, create=True):
    source, payload = read_package(session, task_id, package_id)
    result = storage.export(task_id, package_id, source.checksum, payload, create=create)
    if create:
        # Filesystem and SQLite cannot share a transaction. A retry verifies the
        # completed directory and repairs a missing receipt after a DB failure.
        uri = f"workspace-package:{package_id}:{source.checksum}"
        receipt = session.scalar(select(Artifact).where(Artifact.task_id == task_id, Artifact.name == EXPORT_NAME, Artifact.uri == uri).order_by(Artifact.id).limit(1))
        if receipt is None:
            content = canonical_json({k: v for k, v in result.items() if k != "created"})
            receipt = Artifact(task_id=task_id, project_id=source.project_id, plan_id=source.plan_id,
                               artifact_type=ArtifactType.OTHER, name=EXPORT_NAME, uri=uri,
                               content=content, checksum=sha256(content.encode()).hexdigest(), created_by="owner",
                               description=f"Eksport paczki #{package_id} na dysk Linux; bez wykonania kodu.")
            session.add(receipt)
            session.add(AuditEvent(event_type="workspace_export", operation="export", decision="stored", allowed=True,
                                   reason=f"owner; task={task_id}; package={package_id}; source_sha256={source.checksum}"))
            session.commit()
        result["receipt_id"] = receipt.id
    return result
