"""Native observer UI; guest transport remains the unchanged frame/key protocol."""
import argparse, json, queue, sys, threading, time, tkinter as tk
from tkinter import ttk
from pathlib import Path
from .private_display_protocol import Client
from .private_x11 import W, H, png
from .viewer_state_v2 import Evidence, countdown, CONTROL_NAMES, RESULTS
ALLOWED = {'Left', 'Right', 'Up', 'Down', 'Return', 'Escape', 'space', 'Control_L', 'Alt_L', 'Shift_L', 'Pause', 'Tab', 'BackSpace', *[f'F{i}' for i in range(1, 11)], *'abcdefghijklmnopqrstuvwxyz0123456789'}

class Viewer:

    def __init__(self, args):
        self.args = args
        self.start = time.monotonic()
        self.evidence = Evidence(args.record, self.start, args.deadline, args.harmless_test)
        self.evidence.data['outer_deadline_monotonic'] = args.outer_deadline
        self.evidence.data['accelerated_regression'] = args.accelerated_test
        self.requests = queue.Queue(64)
        self.events = queue.Queue(128)
        self.frames = queue.Queue(1)
        self.stop = threading.Event()
        self.pressed = set()
        self.latest = None
        self.latest_at = 0
        self.focused = False
        self.ended = False
        self.connected = False
        self.root = tk.Tk()
        self.root.title('RE:PLAY — ' + ('Harmless viewer test' if args.harmless_test else 'Supervised gameplay'))
        self.root.configure(bg='#f4f5f6')
        self.root.resizable(False, False)
        style = ttk.Style(self.root)
        style.theme_use('clam')
        style.configure('TFrame', background='#f4f5f6')
        style.configure('TLabel', background='#f4f5f6', foreground='#19202a', font=('TkDefaultFont', 10))
        style.configure('TButton', font=('TkDefaultFont', 10), padding=(10, 7))
        style.configure('End.TButton', foreground='#8c1c13')
        style.configure('TCombobox', padding=3)
        header = ttk.Frame(self.root, padding=(16, 12))
        header.pack(fill='x')
        ttk.Label(header, text='Accelerated harmless test' if args.accelerated_test else '10-minute harmless preview' if args.harmless_test else 'Verify gameplay', font=('TkDefaultFont', 17, 'bold')).pack(side='left')
        self.timer = ttk.Label(header, text='--:-- remaining', font=('TkDefaultFont', 17, 'bold'))
        self.timer.pack(side='right')
        body = ttk.Frame(self.root, padding=(14, 0, 14, 0))
        body.pack(fill='both')
        left = ttk.Frame(body)
        left.pack(side='left', anchor='n')
        self.focus_text = ttk.Label(left, text='Keyboard inactive — click the game image', foreground='#9a3412')
        self.focus_text.pack(anchor='w', pady=(0, 3))
        self.game_timer = ttk.Label(left, text='Emulator stop: waiting for timing', foreground='#45546a')
        self.game_timer.pack(anchor='w', pady=(0, 6))
        self.compact = self.root.winfo_screenheight() < 780
        self.placeholder = tk.PhotoImage(width=400 if self.compact else 800, height=300 if self.compact else 600)
        self.image = tk.Label(left, image=self.placeholder, bg='#080a0c', takefocus=True, highlightthickness=2, highlightbackground='#737b85', highlightcolor='#145a63', bd=0)
        self.image.pack()
        self.image.bind('<Button-1>', lambda e: self.image.focus_set())
        self.side = ttk.Frame(body, padding=(18, 0, 0, 0), width=300)
        self.side.pack(side='left', fill='y', anchor='n')
        self.menu = ttk.Button(self.side, text='Mark menu visible', command=lambda: self.observe('first_visible_game_menu'))
        self.menu.pack(fill='x')
        ttk.Label(self.side, text='Choose New Game, then a difficulty.\nDo not load a saved game.', wraplength=285).pack(anchor='w', pady=(7, 10))
        self.transition = ttk.Button(self.side, text='Mark first level transition', command=lambda: self.observe('first_level_transition'))
        self.transition.pack(fill='x')
        ttk.Label(self.side, text='Confirm MAP01 / Entryway after loading.', wraplength=285).pack(anchor='w', pady=(7, 10))
        self.variables = {}
        self.add_result('MAP01', 'MAP01 loaded')
        for name, label in [('movement', 'Move — Up / Down'), ('turning', 'Turn — Left / Right'), ('firing', 'Fire — Ctrl'), ('use', 'Use a door / switch — Space'), ('pause_resume', 'Pause / resume — Pause/Break'), ('exit_through_game_menu', 'Quit through the game menu')]:
            self.add_result(name, label)
        ttk.Label(self.side, text='Record only what you personally verify.\nKey delivery alone is not a passing test.', wraplength=285).pack(anchor='w', pady=(10, 0))
        footer = ttk.Frame(self.root, padding=(16, 10))
        footer.pack(fill='x')
        self.capture = ttk.Button(footer, text='Capture private frame', command=lambda: self.screenshot('human_capture'))
        self.capture.pack(side='left')
        self.end = ttk.Button(footer, text='End session', style='End.TButton', command=lambda: self.finish('human_end_session', True))
        self.end.pack(side='right')
        self.status = ttk.Label(self.root, text='Connecting to the private display…', padding=(16, 0, 16, 10))
        self.status.pack(anchor='w')
        self.root.bind('<KeyPress>', lambda e: None if self.args.harmless_test else self.key(e.keysym, True))
        self.root.bind('<KeyRelease>', lambda e: None if self.args.harmless_test else self.key(e.keysym, False))
        self.root.bind('<FocusIn>', lambda e: self.root.after_idle(self.update_focus))
        self.root.bind('<FocusOut>', lambda e: self.root.after_idle(self.update_focus))
        self.root.protocol('WM_DELETE_WINDOW', lambda: self.finish('viewer_window_closed', True))
        self.worker = threading.Thread(target=self.network, daemon=True)
        self.worker.start()
        self.root.after(40, self.poll)
        if args.harmless_test:
            self.root.after(600, self.synthetic_test)

    def add_result(self, name, label):
        row = ttk.Frame(self.side)
        row.pack(fill='x', pady=3)
        ttk.Label(row, text=label, wraplength=180).pack(side='left')
        v = tk.StringVar(value='Not tested')
        combo = ttk.Combobox(row, textvariable=v, values=RESULTS, state='readonly', width=11)
        combo.pack(side='right')
        self.variables[name] = v
        combo.bind('<<ComboboxSelected>>', lambda e, n=name: self.confirm(n))

    def confirm(self, name):
        value = self.variables[name].get()
        if name == 'MAP01':
            self.evidence.data['MAP01'] = {'result': value, 'source': 'synthetic_regression' if self.args.harmless_test else 'human_confirmation', 'utc': __import__('replay_preservation.compat.viewer_state_v2', fromlist=['stamp']).stamp()}
        else:
            self.evidence.control(name, value)
        self.status.configure(text='Observation recorded. Click the game image to resume keyboard control.')

    def update_focus(self):
        value = self.root.focus_get() == self.image and self.connected and (not self.ended)
        if value != self.focused:
            self.focused = value
            if len(self.evidence.data['focus_events']) < 256:
                self.evidence.data['focus_events'].append({'focused': value, 'elapsed_seconds': time.monotonic() - self.start})
            if not value:
                self.release_all()
        self.focus_text.configure(text='Keyboard active — controls go to the game' if value else 'Keyboard inactive — click the game image', foreground='#166534' if value else '#9a3412')

    def enqueue(self, event):
        try:
            self.requests.put_nowait(event)
        except queue.Full:
            self.finish('input_queue_overflow', True)

    def key(self, name, down):
        name = {'Control_R': 'Control_L', 'Shift_R': 'Shift_L', 'Alt_R': 'Alt_L'}.get(name, name)
        if self.ended or not self.focused or name not in ALLOWED:
            return
        if down and name in self.pressed:
            return
        self.enqueue((name, down))
        if down:
            self.pressed.add(name)
        else:
            self.pressed.discard(name)

    def release_all(self):
        for name in list(self.pressed):
            self.enqueue((name, False))
        self.pressed.clear()

    def network(self):
        client = None
        try:
            client = Client(self.args.socket)
            self.events.put(('connected', None))
            next_frame = 0
            while not self.stop.is_set():
                try:
                    name, down = self.requests.get(timeout=0.02)
                    client.request('key', key=name, down=down)
                    self.events.put(('key_sent', None), timeout=0.5)
                except queue.Empty:
                    pass
                if time.monotonic() >= next_frame:
                    frame = client.request('frame')
                    if not len(frame) == W * H * 3:
                        raise ValueError('Invalid compatibility-helper state')
                    try:
                        self.frames.get_nowait()
                    except queue.Empty:
                        pass
                    self.frames.put_nowait((frame, time.monotonic()))
                    next_frame = time.monotonic() + 0.15
        except (EOFError, BrokenPipeError, ConnectionResetError):
            self.events.put(('relay_closed', None))
        except Exception as exc:
            self.events.put(('error', type(exc).__name__ + ': ' + str(exc)))
        finally:
            if client:
                client.close()

    def poll(self):
        if self.ended:
            return
        while True:
            try:
                kind, value = self.events.get_nowait()
            except queue.Empty:
                break
            if kind == 'connected':
                self.connected = True
                self.status.configure(text='Running. Observe the menu, start a new MAP01 game, then verify the controls.')
                self.update_focus()
            elif kind == 'key_sent':
                self.evidence.data['key_events_sent'] += 1
            elif kind == 'relay_closed':
                self.finish('private_relay_closed', False)
                return
            else:
                self.evidence.data['errors'].append(value)
                self.finish('display_connection_error', True)
                return
        try:
            frame, when = self.frames.get_nowait()
            self.latest = frame
            self.latest_at = when
            photo = tk.PhotoImage(data=b'P6\n800 600\n255\n' + frame, format='PPM')
            if self.compact:
                photo = photo.subsample(2)
            self.image.configure(image=photo, width=0, height=0)
            self.image.photo = photo
            self.evidence.data['frames_displayed'] += 1
        except queue.Empty:
            pass
        label, outer_left = countdown(self.args.outer_deadline, time.monotonic())
        game_label, left = countdown(self.args.deadline, time.monotonic())
        self.game_timer.configure(text='Emulator stop in ' + game_label + ' · cleanup stays within the outer limit')
        self.timer.configure(text=label + ' outer limit', foreground='#991b1b' if left <= 15 else '#9a3412' if left <= 60 else '#19202a')
        if left == 0:
            self.finish('viewer_deadline', True)
            return
        if left <= 60:
            self.status.configure(text='Time is nearly over. Capture evidence and quit through the game menu. End session stops the emulator.')
        self.root.after(50, self.poll)

    def screenshot(self, reason):
        if self.latest is None:
            return
        try:
            item = self.evidence.save_frame(self.latest, reason, png)
            item['frame_age_seconds'] = max(0, time.monotonic() - self.latest_at)
            self.status.configure(text='Private frame saved with its timestamp and SHA-256.')
        except ValueError as exc:
            self.status.configure(text=str(exc))

    def observe(self, name):
        if self.latest is None or time.monotonic() - self.latest_at > 2:
            self.status.configure(text='Wait for a fresh frame before recording this observation.')
            return
        self.evidence.event(name)
        self.screenshot(name)
        self.status.configure(text='Observation recorded. Click the game image to continue.')

    def finish(self, reason, request_end):
        if self.ended:
            return
        self.ended = True
        self.release_all()
        self.focused = False
        self.focus_text.configure(text='Keyboard inactive — session ending')
        self.timer.configure(text='Session ending')
        self.status.configure(text='Stopping the session. This does not count as quitting through the game menu.')
        self.root.update_idletasks()
        self.screenshot('session_end')
        self.evidence.data['native_window_mapped'] = bool(self.root.winfo_viewable())
        self.evidence.data['compact_view'] = self.compact
        if request_end:
            print(json.dumps({'event': 'end_session_requested', 'reason': reason}), flush=True)
        self.stop.set()
        self.evidence.data['termination_reason'] = reason
        self.root.after(150, self.root.destroy)

    def synthetic_test(self):
        if not self.connected or self.latest is None:
            self.root.after(100, self.synthetic_test)
            return
        self.image.focus_force()
        self.update_focus()
        if not self.focused:
            raise ValueError('Invalid compatibility-helper state')
        self.menu.focus_set()
        self.update_focus()
        if not not self.focused:
            raise ValueError('Invalid compatibility-helper state')
        before = self.evidence.data['key_events_sent']
        self.key('e', True)
        if not self.evidence.data['key_events_sent'] == before:
            raise ValueError('Invalid compatibility-helper state')
        self.menu.invoke()
        self.transition.invoke()
        self.variables['movement'].set('Pass')
        self.confirm('movement')
        self.image.focus_set()
        self.update_focus()
        if not self.focused:
            raise ValueError('Invalid compatibility-helper state')
        sequence = []
        for char in 'echo vtwoinput':
            sequence.extend([('space' if char == ' ' else char, True), ('space' if char == ' ' else char, False)])
        sequence.extend([('Return', True), ('Return', False)])

        def step(i=0):
            if self.ended:
                return
            if i < len(sequence):
                self.key(*sequence[i])
                self.root.after(35, lambda: step(i + 1))
            else:
                self.evidence.data['synthetic_input_queued'] = True
        step()
        self.root.after(2600, lambda: self.screenshot('synthetic_keyboard_evidence'))
        if self.args.owned_ui_capture:
            self.root.after(2800, self.capture_owned_window)
        if self.args.test_end_button:
            self.root.after(3600, self.end.invoke)

    def capture_owned_window(self):
        import ctypes as C, struct, zlib
        from .private_x11 import Display, XImage
        d = Display()
        wid = self.root.winfo_id()
        width, height = (self.root.winfo_width(), self.root.winfo_height())
        if not (width <= 1600 and height <= 1200):
            raise ValueError('Invalid compatibility-helper state')
        im = d.x.XGetImage(d.d, wid, 0, 0, width, height, 18446744073709551615, 2)
        if not im:
            raise ValueError('Invalid compatibility-helper state')
        try:
            i = im.contents
            if not (i.bits_per_pixel == 32 and i.byte_order == 0 and (i.bytes_per_line == width * 4)):
                raise ValueError('Invalid compatibility-helper state')
            raw = C.string_at(i.data, width * height * 4)
            rgb = bytearray(width * height * 3)
            rgb[0::3] = raw[2::4]
            rgb[1::3] = raw[1::4]
            rgb[2::3] = raw[0::4]

            def chunk(k, b):
                return struct.pack('>I', len(b)) + k + b + struct.pack('>I', zlib.crc32(k + b) & 4294967295)
            pixels = b''.join((b'\x00' + rgb[y * width * 3:(y + 1) * width * 3] for y in range(height)))
            data = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(pixels)) + chunk(b'IEND', b'')
            Path(self.args.owned_ui_capture).write_bytes(data)
        finally:
            d.x.XDestroyImage(im)
            d.close()

    def run(self):
        self.root.mainloop()
        self.stop.set()
        self.worker.join(timeout=4)
        while True:
            try:
                kind, value = self.events.get_nowait()
            except queue.Empty:
                break
            if kind == 'key_sent':
                self.evidence.data['key_events_sent'] += 1
        self.evidence.data['network_thread_stopped'] = not self.worker.is_alive()
        self.evidence.finish(self.evidence.data['termination_reason'] or 'viewer_ended')

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--socket', required=True)
    p.add_argument('--record', required=True)
    p.add_argument('--deadline', type=float, required=True)
    p.add_argument('--outer-deadline', type=float)
    p.add_argument('--accelerated-test', action='store_true')
    p.add_argument('--harmless-test', action='store_true')
    p.add_argument('--test-end-button', action='store_true')
    p.add_argument('--owned-ui-capture')
    a = p.parse_args()
    if not 0 < a.deadline - time.monotonic() <= 600:
        raise ValueError('Invalid compatibility-helper state')
    if a.outer_deadline is None:
        a.outer_deadline = a.deadline
    if not (a.deadline <= a.outer_deadline and a.outer_deadline - time.monotonic() <= 600):
        raise ValueError('Invalid compatibility-helper state')
    if a.test_end_button or a.owned_ui_capture or a.accelerated_test:
        if not a.harmless_test:
            raise ValueError('Invalid compatibility-helper state')
    Viewer(a).run()
if __name__ == '__main__':
    main()
