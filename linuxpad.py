#!/usr/bin/env python3
import sys
import os
import json
import subprocess
import signal
import re
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QMenu, QInputDialog, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QFrame, QSplitter, QListWidget, 
    QListWidgetItem, QSlider, QPushButton, QFileDialog, QStyle, QToolBar,
    QSizePolicy, QComboBox, QDialog, QDialogButtonBox, QListView, QLineEdit
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QSize
from PyQt6.QtGui import QShortcut, QKeySequence, QAction, QFont, QColor, QBrush

CONFIG_DIR = Path.home() / ".config" / "linuxpad"
CONFIG_FILE = CONFIG_DIR / "config.json"

DARK_THEME = """
QMainWindow { background-color: #1e1e1e; color: #ffffff; }
QWidget { background-color: #1e1e1e; color: #ffffff; font-family: "Segoe UI", sans-serif; font-size: 13px; }
QToolBar { background-color: #2d2d2d; border-bottom: 1px solid #3d3d3d; spacing: 10px; padding: 5px; }
QToolButton { background-color: transparent; border: 1px solid transparent; border-radius: 3px; padding: 4px; }
QToolButton:hover { background-color: #3d3d3d; border: 1px solid #5294e2; }
QTableWidget {
    background-color: #1e1e1e; gridline-color: #2d2d2d; border: none;
    selection-background-color: #3daee9; selection-color: #ffffff; alternate-background-color: #252525;
}
QHeaderView::section {
    background-color: #2d2d2d; color: #cccccc; border: none;
    border-right: 1px solid #3d3d3d; border-bottom: 1px solid #3d3d3d; padding: 4px;
}
QTableWidget::item { padding: 5px; }
QListWidget { background-color: #252525; border-right: 1px solid #3d3d3d; outline: none; }
QListWidget::item { padding: 10px; color: #cccccc; }
QListWidget::item:selected { background-color: #3daee9; color: white; }
QSlider::groove:horizontal { height: 4px; background: #3d3d3d; border-radius: 2px; }
QSlider::handle:horizontal { background: #3daee9; width: 14px; margin: -5px 0; border-radius: 7px; }
QSlider::sub-page:horizontal { background: #3daee9; border-radius: 2px; }
QFrame#StatusBar { background-color: #2d2d2d; border-top: 1px solid #3d3d3d; }
QLabel#StatusLabel { color: #888888; padding: 0 10px; }
QComboBox {
    background-color: #252525; border: 1px solid #3d3d3d; border-radius: 4px; padding: 4px 8px; min-width: 200px;
}
QComboBox:hover { border: 1px solid #5294e2; }
QComboBox::drop-down { border: none; width: 20px; }
QComboBox::down-arrow { image: none; border-left: 4px solid transparent; border-right: 4px solid transparent; border-top: 6px solid #888; }
QComboBox QAbstractItemView { background-color: #252525; border: 1px solid #3d3d3d; selection-background-color: #3daee9; }
QDialog { background-color: #1e1e1e; }
QLineEdit { background-color: #252525; border: 1px solid #3d3d3d; border-radius: 4px; padding: 5px; color: #ffffff; }
QLineEdit:focus { border: 1px solid #5294e2; }
"""

try:
    from pynput import keyboard
    HAS_PYNPUT = True
except ImportError:
    HAS_PYNPUT = False

class HotkeySignal(QObject):
    triggered = pyqtSignal(str)

class GlobalHotkeyListener:
    def __init__(self, callback):
        self.callback = callback
        self.hotkeys = {}
        self.listener = None
        self.pressed_keys = {}
        self.active = True
    
    def parse(self, h_str):
        h_str = h_str.lower().strip()
        if h_str.startswith("f") and h_str[1:].isdigit():
            return getattr(keyboard.Key, h_str, None)
        elif len(h_str) == 1:
            return h_str
        return None

    def register(self, h_str, f_path):
        try:
            key = self.parse(h_str)
            if key:
                self.hotkeys[key] = f_path
        except: 
            pass

    def clear(self): 
        self.hotkeys.clear()

    def on_press(self, key):
        if not self.active:
            return
        try:
            if hasattr(key, 'char') and key.char:
                check_key = key.char.lower()
            else:
                check_key = key
            key_id = str(check_key)
            if key_id not in self.pressed_keys:
                self.pressed_keys[key_id] = True
                if check_key in self.hotkeys:
                    self.callback(self.hotkeys[check_key])
        except:
            pass

    def on_release(self, key):
        try:
            if hasattr(key, 'char') and key.char:
                check_key = key.char.lower()
            else:
                check_key = key
            key_id = str(check_key)
            self.pressed_keys.pop(key_id, None)
        except:
            pass

    def start(self):
        if HAS_PYNPUT and not self.listener:
            self.active = True
            self.listener = keyboard.Listener(on_press=self.on_press, on_release=self.on_release, suppress=False)
            self.listener.start()
    
    def stop(self):
        self.active = False
        if self.listener:
            self.listener.stop()
            self.listener = None
        self.pressed_keys.clear()


class AudioDeviceManager:
    @staticmethod
    def get_all_targets():
        devices = []
        try:
            result = subprocess.run(["pactl", "list", "sinks", "short"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if not line: continue
                    parts = line.split('\t')
                    if len(parts) >= 2:
                        node_id, name = parts[0], parts[1]
                        display = AudioDeviceManager._format_display_name(name)
                        devices.append({'id': name, 'node_id': node_id, 'name': name, 'display': f"[Sink] {display}", 'type': 'sink'})
        except: pass
        try:
            result = subprocess.run(["pactl", "list", "sources", "short"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if not line: continue
                    parts = line.split('\t')
                    if len(parts) >= 2:
                        node_id, name = parts[0], parts[1]
                        if '.monitor' not in name.lower():
                            display = AudioDeviceManager._format_display_name(name)
                            devices.append({'id': name, 'node_id': node_id, 'name': name, 'display': f"[Source] {display}", 'type': 'source'})
        except: pass
        try:
            result = subprocess.run(["pw-link", "-o"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                seen = set(d['name'] for d in devices)
                for line in result.stdout.strip().split('\n'):
                    if not line or ':' not in line: continue
                    name = line.split(':')[0].strip()
                    if name and name not in seen:
                        display = AudioDeviceManager._format_display_name(name)
                        devices.append({'id': name, 'node_id': '', 'name': name, 'display': f"[Node] {display}", 'type': 'node'})
                        seen.add(name)
        except: pass
        return devices
    
    @staticmethod
    def _format_display_name(name):
        display = name
        for prefix in ['alsa_output.', 'alsa_input.', 'bluez_sink.', 'bluez_source.']:
            if display.startswith(prefix):
                display = display[len(prefix):]
                break
        display = display.replace('_', ' ').replace('.', ' ').replace('-', ' ')
        for suffix in ['.monitor', 'analog stereo', 'pro audio']:
            if suffix in display.lower():
                display = display.lower().replace(suffix, '').strip()
        display = ' '.join(word.capitalize() for word in display.split())
        if len(display) > 50: display = display[:47] + "..."
        return display if display else "Unknown Device"


class DeviceSelectDialog(QDialog):
    def __init__(self, parent=None, current_target=""):
        super().__init__(parent)
        self.current_target = current_target
        self.init_ui()
        self.load_devices()
    
    def init_ui(self):
        self.setWindowTitle("Select Audio Target")
        self.setMinimumSize(500, 400)
        self.setStyleSheet(DARK_THEME)
        layout = QVBoxLayout(self)
        info = QLabel("Select the audio device where sounds will be played.\nFor virtual microphone, select your virtual sink.")
        info.setStyleSheet("color: #888; margin-bottom: 10px;")
        layout.addWidget(info)
        refresh_btn = QPushButton("Refresh Devices")
        refresh_btn.clicked.connect(self.load_devices)
        layout.addWidget(refresh_btn)
        self.device_list = QListWidget()
        self.device_list.setStyleSheet("""
            QListWidget { background: #252525; border: 1px solid #3d3d3d; border-radius: 4px; }
            QListWidget::item { padding: 10px; border-bottom: 1px solid #3d3d3d; }
            QListWidget::item:selected { background: #3daee9; }
            QListWidget::item:hover { background: #353535; }
        """)
        self.device_list.itemDoubleClicked.connect(self.accept)
        layout.addWidget(self.device_list)
        current_frame = QFrame()
        current_frame.setStyleSheet("background: #2d2d2d; border-radius: 4px; padding: 5px;")
        current_layout = QHBoxLayout(current_frame)
        current_layout.addWidget(QLabel("Current:"))
        self.current_label = QLabel(self.current_target or "Not set")
        self.current_label.setStyleSheet("color: #3daee9; font-weight: bold;")
        current_layout.addWidget(self.current_label)
        current_layout.addStretch()
        layout.addWidget(current_frame)
        manual_layout = QHBoxLayout()
        manual_layout.addWidget(QLabel("Manual ID:"))
        self.manual_entry = QLineEdit()
        self.manual_entry.setPlaceholderText("Enter device name/ID manually...")
        manual_layout.addWidget(self.manual_entry)
        layout.addLayout(manual_layout)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def load_devices(self):
        self.device_list.clear()
        devices = AudioDeviceManager.get_all_targets()
        for dev in devices:
            item = QListWidgetItem()
            item.setText(f"{dev['display']}\n  ID: {dev['id']}")
            item.setData(Qt.ItemDataRole.UserRole, dev['id'])
            if dev['id'] == self.current_target:
                item.setBackground(QBrush(QColor("#2d4a2d")))
            if any(x in dev['name'].lower() for x in ['virtual', 'null', 'mic', 'soundboard', 'easyeffects']):
                font = item.font()
                font.setBold(True)
                item.setFont(font)
            self.device_list.addItem(item)
        if not devices:
            item = QListWidgetItem("No devices found")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.device_list.addItem(item)
    
    def get_selected_device(self):
        manual = self.manual_entry.text().strip()
        if manual: return manual
        current = self.device_list.currentItem()
        if current:
            device_id = current.data(Qt.ItemDataRole.UserRole)
            if device_id: return device_id
        return None


class SoundpadWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.sounds = []
        self.proc_mic = None
        self.proc_local = None
        self.current_playing_path = None
        self.target = ""
        self.vol_mic = 100
        self.vol_local = 50
        self.hk_sig = HotkeySignal()
        self.hk_sig.triggered.connect(self.play_file_toggle)
        self.ghk = GlobalHotkeyListener(lambda fp: self.hk_sig.triggered.emit(fp))
        self.init_ui()
        self.load_config()
        self.refresh_table()
        self.ghk.start()

    def init_ui(self):
        self.setWindowTitle("LinuxPad")
        self.resize(950, 600)
        self.setStyleSheet(DARK_THEME)
        toolbar = QToolBar()
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(toolbar)
        style = self.style()
        play_act = QAction(style.standardIcon(QStyle.StandardPixmap.SP_MediaPlay), "Play", self)
        play_act.triggered.connect(self.play_selected)
        toolbar.addAction(play_act)
        stop_act = QAction(style.standardIcon(QStyle.StandardPixmap.SP_MediaStop), "Stop", self)
        stop_act.triggered.connect(self.stop_sound)
        toolbar.addAction(stop_act)
        add_act = QAction(style.standardIcon(QStyle.StandardPixmap.SP_FileDialogNewFolder), "Add", self)
        add_act.triggered.connect(self.add_files)
        toolbar.addAction(add_act)
        toolbar.addSeparator()
        lbl_target = QLabel(" Target: ")
        lbl_target.setStyleSheet("color: #aaa;")
        toolbar.addWidget(lbl_target)
        self.btn_target = QPushButton("Select Device...")
        self.btn_target.setStyleSheet("""
            QPushButton { background: #252525; border: 1px solid #3d3d3d; color: #3daee9; border-radius: 4px; padding: 5px 15px; font-weight: bold; }
            QPushButton:hover { border: 1px solid #5294e2; background: #353535; }
        """)
        self.btn_target.clicked.connect(self.change_target)
        toolbar.addWidget(self.btn_target)
        dummy = QWidget()
        dummy.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        toolbar.addWidget(dummy)
        lbl_mic = QLabel(" Mic: ")
        lbl_mic.setStyleSheet("color: #e94560; font-weight: bold;")
        toolbar.addWidget(lbl_mic)
        self.slider_mic = QSlider(Qt.Orientation.Horizontal)
        self.slider_mic.setRange(0, 100)
        self.slider_mic.setValue(100)
        self.slider_mic.setFixedWidth(80)
        self.slider_mic.valueChanged.connect(lambda v: self.lbl_mic_val.setText(f"{v}%"))
        self.slider_mic.valueChanged.connect(lambda v: setattr(self, 'vol_mic', v))
        toolbar.addWidget(self.slider_mic)
        self.lbl_mic_val = QLabel("100% ")
        self.lbl_mic_val.setFixedWidth(35)
        toolbar.addWidget(self.lbl_mic_val)
        lbl_local = QLabel(" Local: ")
        lbl_local.setStyleSheet("color: #3daee9; font-weight: bold;")
        toolbar.addWidget(lbl_local)
        self.slider_local = QSlider(Qt.Orientation.Horizontal)
        self.slider_local.setRange(0, 100)
        self.slider_local.setValue(50)
        self.slider_local.setFixedWidth(80)
        self.slider_local.valueChanged.connect(lambda v: self.lbl_local_val.setText(f"{v}%"))
        self.slider_local.valueChanged.connect(lambda v: setattr(self, 'vol_local', v))
        toolbar.addWidget(self.slider_local)
        self.lbl_local_val = QLabel("50% ")
        self.lbl_local_val.setFixedWidth(35)
        toolbar.addWidget(self.lbl_local_val)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.sidebar = QListWidget()
        self.sidebar.setFixedWidth(200)
        item = QListWidgetItem("My Sounds")
        item.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_DirHomeIcon))
        self.sidebar.addItem(item)
        self.sidebar.setCurrentRow(0)
        splitter.addWidget(self.sidebar)
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["#", "Hotkey", "Name", "File Path"])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.table.cellDoubleClicked.connect(self.play_selected)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.table_context_menu)
        splitter.addWidget(self.table)
        splitter.setStretchFactor(1, 1)
        self.setAcceptDrops(True)
        self.table.setAcceptDrops(False)
        self.status_bar = QFrame()
        self.status_bar.setObjectName("StatusBar")
        self.status_bar.setFixedHeight(30)
        sb_layout = QHBoxLayout(self.status_bar)
        sb_layout.setContentsMargins(0, 0, 0, 0)
        self.lbl_status = QLabel("Ready")
        self.lbl_status.setObjectName("StatusLabel")
        sb_layout.addWidget(self.lbl_status)
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(0,0,0,0)
        main_layout.setSpacing(0)
        main_layout.addWidget(splitter)
        main_layout.addWidget(self.status_bar)
        self.setCentralWidget(main_widget)
        QShortcut(QKeySequence("Escape"), self).activated.connect(self.stop_sound)
        QShortcut(QKeySequence("Delete"), self).activated.connect(self.remove_selected)

    def update_target_button(self):
        if self.target:
            display = AudioDeviceManager._format_display_name(self.target)
            if len(display) > 25: display = display[:22] + "..."
            self.btn_target.setText(display)
            self.btn_target.setToolTip(f"Target: {self.target}")
        else:
            self.btn_target.setText("Select Device...")

    def refresh_table(self):
        self.table.setRowCount(0)
        for i, s in enumerate(self.sounds):
            self.table.insertRow(i)
            idx_item = QTableWidgetItem(str(i + 1))
            idx_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(i, 0, idx_item)
            hk = s.get("hotkey", "")
            hk_item = QTableWidgetItem(hk)
            if hk:
                hk_item.setForeground(QBrush(QColor("#e94560")))
                hk_item.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
            hk_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(i, 1, hk_item)
            self.table.setItem(i, 2, QTableWidgetItem(s.get("name", "Unknown")))
            path_item = QTableWidgetItem(str(s.get("file", "")))
            path_item.setForeground(QBrush(QColor("#666666")))
            self.table.setItem(i, 3, path_item)
        self.lbl_status.setText(f"Total sounds: {len(self.sounds)}")
        self.setup_global_hotkeys()

    def add_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Select Audio", "", "Audio (*.mp3 *.wav *.ogg *.flac *.m4a *.opus *.aac)")
        if files:
            for f in files:
                self.sounds.append({"file": f, "name": Path(f).stem, "hotkey": ""})
            self.save_config()
            self.refresh_table()

    def play_selected(self):
        row = self.table.currentRow()
        if 0 <= row < len(self.sounds):
            self.play_file(self.sounds[row]["file"])

    def play_file_toggle(self, fp):
        if self.current_playing_path == fp:
            self.stop_sound()
            return
        self.play_file(fp)

    def play_file(self, fp):
        if not fp or not os.path.exists(fp): 
            self.lbl_status.setText(f"File not found: {fp}")
            return
        if not self.target:
            self.lbl_status.setText("No target device selected!")
            return
        self.stop_sound()
        try:
            mic_vol_float = self.vol_mic / 100.0
            self.proc_mic = subprocess.Popen(
                ["pw-play", "--target", self.target, "--volume", str(mic_vol_float), fp],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            if self.vol_local > 0:
                local_vol_float = self.vol_local / 100.0
                self.proc_local = subprocess.Popen(
                    ["pw-play", "--volume", str(local_vol_float), fp],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
            self.current_playing_path = fp
            self.lbl_status.setText(f"Playing: {Path(fp).name}")
        except FileNotFoundError:
            self.lbl_status.setText("Error: pw-play not found. Install pipewire.")
        except Exception as e:
            self.lbl_status.setText(f"Error: {e}")

    def stop_sound(self):
        for proc in [self.proc_mic, self.proc_local]:
            if proc:
                try:
                    proc.send_signal(signal.SIGINT)
                    proc.wait(timeout=0.1)
                except:
                    try: proc.kill()
                    except: pass
        self.proc_mic = self.proc_local = None
        self.current_playing_path = None
        self.lbl_status.setText("Stopped")

    def change_target(self):
        dialog = DeviceSelectDialog(self, self.target)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            device = dialog.get_selected_device()
            if device:
                self.target = device
                self.update_target_button()
                self.save_config()

    def table_context_menu(self, pos):
        row = self.table.rowAt(pos.y())
        if row == -1: return
        self.table.selectRow(row)
        menu = QMenu()
        menu.setStyleSheet("QMenu { background: #2d2d2d; color: white; border: 1px solid #3d3d3d; } QMenu::item:selected { background: #3daee9; }")
        act_hk = menu.addAction("Set Hotkey")
        act_ren = menu.addAction("Rename")
        menu.addSeparator()
        act_del = menu.addAction("Delete")
        res = menu.exec(self.table.viewport().mapToGlobal(pos))
        if res == act_hk: self.set_hotkey(row)
        elif res == act_ren: self.rename_sound(row)
        elif res == act_del: self.remove_selected()

    def set_hotkey(self, row):
        curr = self.sounds[row].get("hotkey", "")
        hk, ok = QInputDialog.getText(self, "Set Hotkey", "Key combo (e.g. F1, A, 1):", text=curr)
        if ok:
            self.sounds[row]["hotkey"] = hk.upper()
            self.save_config()
            self.refresh_table()

    def rename_sound(self, row):
        curr = self.sounds[row]["name"]
        name, ok = QInputDialog.getText(self, "Rename", "Name:", text=curr)
        if ok and name:
            self.sounds[row]["name"] = name
            self.save_config()
            self.refresh_table()

    def remove_selected(self):
        row = self.table.currentRow()
        if row >= 0:
            self.sounds.pop(row)
            self.save_config()
            self.refresh_table()

    def setup_global_hotkeys(self):
        self.ghk.clear()
        for s in self.sounds:
            if s.get("hotkey") and s.get("file"):
                self.ghk.register(s["hotkey"], s["file"])

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls(): e.accept()
    
    def dropEvent(self, e):
        exts = {".mp3", ".wav", ".ogg", ".flac", ".m4a", ".opus", ".aac"}
        for u in e.mimeData().urls():
            fp = u.toLocalFile()
            if Path(fp).suffix.lower() in exts:
                self.sounds.append({"file": fp, "name": Path(fp).stem, "hotkey": ""})
        self.save_config()
        self.refresh_table()

    def load_config(self):
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE) as f:
                    d = json.load(f)
                    self.sounds = d.get("sounds", [])
                    self.target = d.get("target", "")
                    self.vol_local = d.get("vol_local", 50)
                    self.vol_mic = d.get("vol_mic", 100)
                    self.update_target_button()
                    self.slider_mic.setValue(self.vol_mic)
                    self.lbl_mic_val.setText(f"{self.vol_mic}%")
                    self.slider_local.setValue(self.vol_local)
                    self.lbl_local_val.setText(f"{self.vol_local}%")
            except: pass

    def save_config(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            json.dump({"sounds": self.sounds, "target": self.target, "vol_mic": self.vol_mic, "vol_local": self.vol_local}, f, indent=2)

    def closeEvent(self, e):
        self.stop_sound()
        self.ghk.stop()
        e.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    w = SoundpadWindow()
    w.show()
    sys.exit(app.exec())
