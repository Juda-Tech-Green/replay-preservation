"""Pure evidence/state policy, independent of graphical and guest APIs."""
import datetime, hashlib, math, time
from pathlib import Path
OUTER_SECONDS = 600
GAME_SECONDS = 570
CPU_SECONDS = 660
AS_BYTES = 1073741824
CONTROL_NAMES = ('movement', 'turning', 'firing', 'use', 'pause_resume', 'exit_through_game_menu')
RESULTS = ('Not tested', 'Pass', 'Fail', 'Not reached')

def stamp():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def countdown(deadline, now):
    seconds = max(0, math.ceil(deadline - now))
    return (f'{seconds // 60:02d}:{seconds % 60:02d}', seconds)

class Evidence:

    def __init__(self, record_path, start, deadline, synthetic=False):
        self.path = Path(record_path)
        self.start = start
        self.deadline = deadline
        self.data = {'schema': 'replay.graphical.viewer.v2', 'started_utc': stamp(), 'deadline_monotonic': deadline, 'synthetic_test': synthetic, 'frames_displayed': 0, 'key_events_sent': 0, 'screenshots': [], 'observations': {}, 'controls': {name: {'result': 'Not tested', 'source': 'not_confirmed'} for name in CONTROL_NAMES}, 'focus_events': [], 'errors': [], 'screenshot_bytes': 0, 'termination_reason': None}

    def event(self, name, source='human_confirmation', now=None, **extra):
        now = time.monotonic() if now is None else now
        value = {'utc': stamp(), 'elapsed_seconds': max(0, now - self.start), 'source': 'synthetic_regression' if self.data['synthetic_test'] else source, **extra}
        self.data['observations'].setdefault(name, value)
        return value

    def control(self, name, result):
        if not (name in CONTROL_NAMES and result in RESULTS):
            raise ValueError('Invalid compatibility-helper state')
        self.data['controls'][name] = {'result': result, 'utc': stamp(), 'elapsed_seconds': time.monotonic() - self.start, 'source': 'synthetic_regression' if self.data['synthetic_test'] else 'human_confirmation'}

    def save_frame(self, rgb, reason, encoder):
        if len(self.data['screenshots']) >= 32:
            raise ValueError('Screenshot limit reached (32 frames).')
        content = encoder(rgb)
        if self.data['screenshot_bytes'] + len(content) > 50 * 1024 * 1024:
            raise ValueError('Screenshot storage limit reached (50 MiB).')
        path = self.path.with_name(self.path.stem + f"-frame-{len(self.data['screenshots']) + 1:02d}.png")
        with path.open('xb') as f:
            f.write(content)
        item = {'path': str(path), 'sha256': hashlib.sha256(content).hexdigest(), 'utc': stamp(), 'elapsed_seconds': time.monotonic() - self.start, 'reason': reason, 'size': len(content)}
        self.data['screenshots'].append(item)
        self.data['screenshot_bytes'] += len(content)
        return item

    def finish(self, reason):
        self.data['termination_reason'] = reason
        self.data['ended_utc'] = stamp()
        self.data['elapsed_seconds'] = time.monotonic() - self.start
        import json
        self.path.write_text(json.dumps(self.data, indent=2) + '\n')
