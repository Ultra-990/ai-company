"""Bounded owner-only source comparison. No execution, inference or mutations."""
from difflib import unified_diff

from app.services.workspace_packages import read_package, PackageNotFound

MAX_DIFF_BYTES = 16 * 1024
MAX_DIFF_LINES = 300
MAX_OUTPUT_BYTES = 48 * 1024


def compare(session, task_id, package_id, base_id, path=None):
    target, current = read_package(session, task_id, package_id)
    base, previous = read_package(session, task_id, base_id)
    old = {f['path']: f for f in previous['files']}
    new = {f['path']: f for f in current['files']}
    files, counts = [], dict(added=0, removed=0, modified=0, unchanged=0)
    for name in sorted(old.keys() | new.keys()):
        before, after = old.get(name), new.get(name)
        status = ('added' if before is None else 'removed' if after is None else
                  'unchanged' if before['sha256'] == after['sha256'] else 'modified')
        counts[status] += 1
        metadata = lambda f: {k: f[k] for k in ('size_bytes', 'sha256')} if f else None
        files.append(dict(path=name, status=status, before=metadata(before), after=metadata(after)))
    result = dict(schema='package-comparison.v1', task_id=task_id,
                  base_id=base.id, base_checksum=base.checksum,
                  package_id=target.id, package_checksum=target.checksum,
                  counts=counts, files=files, executed=False, accepted=False)
    if path is not None:
        if path not in old and path not in new:
            raise PackageNotFound('Nie znaleziono pliku w porównywanych paczkach.')
        left, right = old.get(path, {}).get('content', ''), new.get(path, {}).get('content', '')
        detail = dict(path=path, available=False, diff=None, reason=None)
        # Bound work before SequenceMatcher (quadratic worst case). Also bound output.
        if any(entry.get('encoding') == 'base64' for entry in (old.get(path, {}), new.get(path, {}))):
            detail['reason'] = 'Obraz binarny: porównaj sumy kontrolne lub pobierz paczki, aby obejrzeć zdjęcia.'
        elif any(len(s.encode('utf-8')) > MAX_DIFF_BYTES or
               len(s.splitlines()) > MAX_DIFF_LINES for s in (left, right)):
            detail['reason'] = 'Plik przekracza limit 16 KiB lub 300 wierszy; pobierz paczki do przeglądu poza panelem.'
        else:
            # Normalise line endings for readability but disclose exact byte changes.
            diff = '\n'.join(unified_diff(left.splitlines(), right.splitlines(),
                                        fromfile=f'base/{path}', tofile=f'current/{path}', lineterm=''))
            if len(diff.encode('utf-8')) > MAX_OUTPUT_BYTES:
                detail['reason'] = 'Porównanie przekracza limit wyświetlania 48 KiB.'
            else:
                detail.update(available=True, diff=diff,
                              line_endings_or_final_newline_only=left != right and not diff)
        result['detail'] = detail
    return result
