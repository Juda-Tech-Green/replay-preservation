"""ZIP only: extraction into a new destination, limits, and unsafe path rejection.
Other formats require an isolated workflow and explicit subsequent review.
"""
import os
import re
import shutil
import stat
import zipfile
from pathlib import Path, PurePosixPath


def safe_member(name):
    if '\\' in name or '\x00' in name or re.match(r'^[A-Za-z]:', name):
        raise ValueError(f'Unsafe member: {name!r}')
    path = PurePosixPath(name)
    if path.is_absolute() or '..' in path.parts or not path.parts:
        raise ValueError(f'Unsafe member: {name!r}')
    return path


def inspect_zip(source, max_files=10000, max_bytes=1024**3, max_ratio=200):
    records = []
    total = 0
    names = set()
    with zipfile.ZipFile(source) as archive:
        if len(archive.infolist()) > max_files:
            raise ValueError('Too many archive members')
        for info in archive.infolist():
            path = safe_member(info.filename)
            key = str(path).casefold()
            if key in names:
                raise ValueError('Duplicate or case-colliding member')
            names.add(key)
            mode = info.external_attr >> 16
            kind = stat.S_IFMT(mode)
            if kind not in (0, stat.S_IFREG, stat.S_IFDIR):
                raise ValueError('Links and special files are forbidden')
            if info.flag_bits & 1:
                raise ValueError('Encrypted member requires manual handling')
            total += info.file_size
            if total > max_bytes or info.file_size > max(1,info.compress_size)*max_ratio:
                raise ValueError('Archive exceeds expansion limits')
            records.append({'name': info.filename, 'size': info.file_size,
                            'compressed_size': info.compress_size, 'crc32': f'{info.CRC:08x}',
                            'zip_date_time': info.date_time, 'external_attr': info.external_attr})
    return records


def extract_zip(source, destination, max_files=10000, max_bytes=1024**3, max_ratio=200):
    """No recursion or execution. zipfile verifies CRC at the end of each member.
    Destination must have a private trusted parent with no concurrent writers.
    Returns ZIP metadata for recording; executable permissions are not applied.
    """
    source, destination = Path(source), Path(destination)
    records = inspect_zip(source, max_files, max_bytes, max_ratio)
    destination.mkdir(mode=0o700, parents=False, exist_ok=False)
    total = 0
    try:
        with zipfile.ZipFile(source) as archive:
            for info in archive.infolist():
                relative = safe_member(info.filename)
                target = destination.joinpath(*relative.parts)
                if info.is_dir():
                    target.mkdir(parents=True, exist_ok=True, mode=0o700)
                    continue
                target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                count = 0
                with archive.open(info) as reader, target.open('xb') as writer:
                    os.chmod(target, 0o600)
                    while block := reader.read(65536):
                        total += len(block)
                        count += len(block)
                        if total > max_bytes or count > info.file_size:
                            raise ValueError('Actual expansion exceeds limit')
                        writer.write(block)
                if count != info.file_size:
                    raise ValueError('Incomplete archive member')
    except BaseException:
        # Evidence remains intact; partial output is never presented as complete.
        shutil.rmtree(destination)
        raise
    return records
