"""Conservative header classification; does not validate or execute programs."""
import struct


def classify(data: bytes, name: str = '') -> dict:
    result = {'format': 'unknown', 'platform': 'unknown', 'confidence': 'unknown'}
    for signature, fmt in [
        (b'PK\x03\x04', 'ZIP'), (b'PK\x05\x06', 'ZIP'),
        (b'7z\xbc\xaf\x27\x1c', '7z'), (b'Rar!\x1a\x07', 'RAR'),
        (b'MSCF', 'CAB'), (b'\x60\xea', 'ARJ'),
        (b'\x7fELF', 'ELF'), (b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1', 'OLE'),
    ]:
        if data.startswith(signature):
            return dict(result, format=fmt, confidence='signature')
    if len(data) >= 7 and data[2:7] in (b'-lh0-', b'-lh1-', b'-lh2-', b'-lh3-', b'-lh4-', b'-lh5-', b'-lh6-', b'-lh7-', b'-lhd-'):
        return dict(result, format='LZH', confidence='signature')
    if data.startswith(b'MZ'):
        result.update(format='MZ', platform='DOS or extended executable', confidence='signature')
        if len(data) < 64:
            return dict(result, warning='truncated MZ header')
        offset = struct.unpack_from('<I', data, 0x3c)[0]
        if offset >= 64 and offset + 4 <= len(data):
            sig = data[offset:offset+4]
            if sig == b'PE\0\0':
                result.update(format='PE', platform='PE target undetermined')
                if offset + 26 <= len(data):
                    result['machine'] = hex(struct.unpack_from('<H', data, offset+4)[0])
                    optional_size = struct.unpack_from('<H', data, offset+20)[0]
                    optional = offset + 24
                    if optional_size >= 70 and optional + optional_size <= len(data):
                        magic = struct.unpack_from('<H', data, optional)[0]
                        subsystem = struct.unpack_from('<H', data, optional+68)[0]
                        result.update(optional_magic=hex(magic), subsystem=subsystem)
                        if magic in (0x10b, 0x20b) and subsystem in (2, 3):
                            result['platform'] = 'Windows PE (version undetermined)'
            elif sig[:2] == b'NE':
                result.update(format='NE', platform='NE target undetermined')
                if offset + 0x37 <= len(data):
                    target = data[offset + 0x36]
                    result['target_os'] = target
                    result['platform'] = {1:'OS/2', 2:'Windows 16-bit', 3:'DOS 4.x', 4:'Windows 386'}.get(target, 'NE target undetermined')
            elif sig[:2] in (b'LE', b'LX'):
                result.update(format=sig[:2].decode(), platform='linear executable; target undetermined')
        elif offset >= 64:
            result['warning'] = 'extended header outside supplied bytes; inspect full file'
        return result
    if name.lower().endswith('.com'):
        return dict(result, format='COM candidate', platform='DOS estimate', confidence='extension_only')
    if name.lower().endswith(('.bat', '.scr', '.exe', '.msi', '.dll')):
        result['warning'] = 'extension is not proof of format; never execute automatically'
    return result
