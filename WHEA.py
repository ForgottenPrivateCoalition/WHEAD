import sys
import os
import winsound
import json
import win32evtlog
import pywintypes
import ctypes
import tempfile
import subprocess
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QWidget, QGroupBox, QCheckBox, QLineEdit,
    QPushButton, QFileDialog, QTextEdit, QLabel, QHBoxLayout, QVBoxLayout,
    QSystemTrayIcon, QMenu, QMessageBox, QDialog
)
from PyQt6.QtGui import QPalette, QColor, QIntValidator, QIcon, QAction, QKeySequence
from PyQt6.QtCore import Qt, QTimer, QSharedMemory, QEvent


APPDATA_DIR = os.path.join(os.getenv("APPDATA"), "Forgotten", "WHEAD")
os.makedirs(APPDATA_DIR, exist_ok=True)

LOG_FILE_PATH = os.path.join(APPDATA_DIR, "LTC-Logger.log")
CONFIG_PATH = os.path.join(APPDATA_DIR, "LTC-Cursed.forgotten")
ERRORS_LOG_PATH = os.path.join(APPDATA_DIR, "LTC-Errors.log")


def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def write_log(text: str):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    try:
        with open(LOG_FILE_PATH, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {text}\n")
    except Exception:
        pass


def write_error_log(text: str):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    try:
        with open(ERRORS_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {text}\n")
    except Exception:
        pass


def event_to_dict(event):
    d = {}
    for attr in dir(event):
        if attr.startswith('_'):
            continue
        try:
            val = getattr(event, attr)
            if callable(val):
                continue
            if isinstance(val, (datetime, pywintypes.Time)):
                val = str(val)
            d[attr] = val
        except Exception:
            continue
    return d


def show_messagebox(text, title="WHEA Monitor"):
    ctypes.windll.user32.MessageBoxW(0, text, title, 0x40)  # MB_ICONINFORMATION


class TriggerSettingsForm(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Настройка триггера")
        icon_path = resource_path("icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        self.setFixedSize(450, 520)

        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(45, 45, 45))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(220, 220, 220))
        self.setPalette(palette)

        self.setStyleSheet("""
            QWidget { background-color: #1e1f26; color: #e0e0e0; font-family: 'Segoe UI'; font-size: 14px; }
            QGroupBox { background-color: #323232; border: 1px solid gray; border-radius: 4px; margin-top: 4px; padding: 8px; min-height: 130px; }
            QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 0 5px; color: #F0F0F0; font-weight: bold; font-size: 15px; }
            QCheckBox { color: #F0F0F0; spacing: 6px; padding: 2px 0; font-size: 14px; background-color: transparent; }
            QLabel { background-color: transparent; color: #F0F0F0; font-size: 14px; }
            QLineEdit { background-color: #2c2d35; border: 1px solid #444; border-radius: 6px; padding: 6px 8px; color: #fff; min-height: 20px; font-size: 14px; }
            QPushButton { background-color: #3f51b5; border-radius: 6px; color: white; padding: 4px 10px; min-height: 28px; }
            QPushButton:hover { background-color: #303f9f; }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(6)

        # Message panel
        self.group_message = QGroupBox("Сообщение")
        layout_msg = QVBoxLayout(self.group_message)
        self.checkbox_msg_enable = QCheckBox("Включить")
        self.checkbox_msg_enable.stateChanged.connect(self.on_message_enable_changed)
        self.checkbox_msg_custom = QCheckBox("Кастомный текст")
        self.checkbox_msg_custom.setEnabled(False)
        self.checkbox_msg_custom.stateChanged.connect(self.on_custom_text_changed)
        self.line_message = QLineEdit()
        self.line_message.setPlaceholderText("Сообщение")
        self.line_message.setEnabled(False)
        layout_msg.addWidget(self.checkbox_msg_enable)
        layout_msg.addWidget(self.checkbox_msg_custom)
        layout_msg.addWidget(self.line_message)
        layout_msg.addStretch()
        main_layout.addWidget(self.group_message)

        # Sound panel
        self.group_audio = QGroupBox("Звук")
        layout_audio = QVBoxLayout(self.group_audio)
        self.checkbox_audio_enable = QCheckBox("Включить")
        self.checkbox_audio_enable.stateChanged.connect(self.update_audio_controls)
        layout_audio.addWidget(self.checkbox_audio_enable)
        self.sounds = [
            ("Windows Background", r"C://Windows//Media//Windows Background.wav"),
            ("System Notify", r"C://Windows//Media//Windows Notify System Generic.wav"),
            ("Critical Stop", r"C://Windows//Media//Windows Critical Stop.wav")
        ]
        self.sound_buttons = []
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(8)
        for idx, (name, path) in enumerate(self.sounds):
            btn = QPushButton(name)
            btn.setEnabled(False)
            btn.setFixedHeight(28)
            btn.clicked.connect(self.make_sound_button_handler(idx, path))
            self.sound_buttons.append(btn)
            buttons_layout.addWidget(btn)
        layout_audio.addLayout(buttons_layout)
        self.label_selected_sound = QLabel("Выбран звук: —")
        self.label_selected_sound.setStyleSheet("background-color: transparent; margin-top: 8px;")
        layout_audio.addWidget(self.label_selected_sound)
        layout_audio.addStretch()
        main_layout.addWidget(self.group_audio)

        # Execute panel
        self.group_execute = QGroupBox("Запуск")
        layout_exec = QVBoxLayout(self.group_execute)
        self.checkbox_exec_enable = QCheckBox("Включить")
        self.checkbox_exec_enable.stateChanged.connect(self.update_execute_controls)
        layout_exec.addWidget(self.checkbox_exec_enable)
        path_layout = QHBoxLayout()
        self.line_program = QLineEdit()
        self.line_program.setPlaceholderText("Путь к программе")
        self.btn_browse = QPushButton("Обзор")
        self.btn_browse.clicked.connect(self.browse_program)
        self.btn_browse.setEnabled(False)
        path_layout.addWidget(self.line_program)
        path_layout.addWidget(self.btn_browse)
        layout_exec.addLayout(path_layout)
        self.line_args = QLineEdit()
        self.line_args.setPlaceholderText("Аргумент запуска")
        self.line_args.setEnabled(False)
        layout_exec.addWidget(self.line_args)
        layout_exec.addStretch()
        main_layout.addWidget(self.group_execute)

        self.selected_audio_index = None
        self.load_config()
        self.update_message_controls()
        self.update_audio_controls()
        self.update_execute_controls()

    def on_message_enable_changed(self, state):
        enabled = self.checkbox_msg_enable.isChecked()
        self.checkbox_msg_custom.setEnabled(enabled)
        if not enabled:
            # Если выключаем основное сообщение — сбрасываем кастомный текст и поле ввода
            self.checkbox_msg_custom.setChecked(False)
            self.line_message.clear()
            self.line_message.setEnabled(False)
        else:
            self.line_message.setEnabled(self.checkbox_msg_custom.isChecked())

    def on_custom_text_changed(self, state):
        enabled = self.checkbox_msg_custom.isChecked()
        self.line_message.setEnabled(enabled)
        if not enabled:
            self.line_message.clear()

    def update_message_controls(self):
        enabled = self.checkbox_msg_enable.isChecked()
        self.checkbox_msg_custom.setEnabled(enabled)
        self.line_message.setEnabled(enabled and self.checkbox_msg_custom.isChecked())

    def update_audio_controls(self):
        enabled = self.checkbox_audio_enable.isChecked()
        for btn in self.sound_buttons:
            btn.setEnabled(enabled)
        if not enabled:
            self.selected_audio_index = None
            self.label_selected_sound.setText("Выбран звук: —")
        else:
            if self.selected_audio_index is not None:
                self.label_selected_sound.setText(f"Выбран звук: {self.sounds[self.selected_audio_index][0]}")
            else:
                self.label_selected_sound.setText("Выбран звук: —")

    def update_execute_controls(self):
        enabled = self.checkbox_exec_enable.isChecked()
        self.line_program.setEnabled(enabled)
        self.btn_browse.setEnabled(enabled)
        self.line_args.setEnabled(enabled)

    def make_sound_button_handler(self, idx, path):
        def handler():
            if os.path.exists(path):
                winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC)
                self.selected_audio_index = idx
                self.label_selected_sound.setText(f"Выбран звук: {self.sounds[idx][0]}")
        return handler

    def browse_program(self):
        path, _ = QFileDialog.getOpenFileName(self, "Выберите .exe или .bat", "", "Executable Files (*.exe *.bat)")
        if path:
            self.line_program.setText(path)

    def get_current_config(self):
        return {
            "message_enabled": self.checkbox_msg_enable.isChecked(),
            "message_custom_enabled": self.checkbox_msg_custom.isChecked(),
            "message_text": self.line_message.text(),
            "audio_enabled": self.checkbox_audio_enable.isChecked(),
            "audio_selected_index": self.selected_audio_index,
            "execute_enabled": self.checkbox_exec_enable.isChecked(),
            "execute_path": self.line_program.text(),
            "execute_args": self.line_args.text(),
        }

    def load_config(self):
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    self.checkbox_msg_enable.setChecked(cfg.get("message_enabled", False))
                    self.checkbox_msg_custom.setChecked(cfg.get("message_custom_enabled", False))
                    self.line_message.setText(cfg.get("message_text", ""))
                    self.checkbox_audio_enable.setChecked(cfg.get("audio_enabled", False))
                    idx = cfg.get("audio_selected_index")
                    self.selected_audio_index = idx if idx in [0, 1, 2] else None
                    if self.selected_audio_index is not None:
                        self.label_selected_sound.setText(f"Выбран звук: {self.sounds[self.selected_audio_index][0]}")
                    else:
                        self.label_selected_sound.setText("Выбран звук: —")
                    self.checkbox_exec_enable.setChecked(cfg.get("execute_enabled", False))
                    self.line_program.setText(cfg.get("execute_path", ""))
                    self.line_args.setText(cfg.get("execute_args", ""))
            except Exception as e:
                write_log(f"Ошибка загрузки конфигурации: {e}")

    def closeEvent(self, event):
        """Переопределение метода closeEvent для сохранения конфигурации при закрытии формы."""
        self.save_config()  # Сохраняем конфигурацию триггера перед закрытием
        event.accept()  # Разрешаем закрытие окна

    def save_config(self):
        cfg = self.get_current_config()
        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2, ensure_ascii=False)
            write_log("Конфигурация триггера сохранена")
            if hasattr(self, 'save_callback') and self.save_callback:
                self.save_callback(cfg)
        except Exception as e:
            write_log(f"Ошибка сохранения конфигурации триггера: {e}")

class WheaMonitorApp(QWidget):
    WHEA_EVENT_IDS = {17, 18, 19, 20, 41, 45, 46, 47}

    def __init__(self):
        super().__init__()

        self.instance_check = QSharedMemory("WHEA_MONITOR_APP_KEY")
        if self.instance_check.attach():
            QMessageBox.warning(None, "WHEA Monitor", "Приложение уже запущено.")
            sys.exit(0)
        if not self.instance_check.create(1):
            QMessageBox.warning(None, "WHEA Monitor", "Не удалось создать разделяемую память.")
            sys.exit(1)

        self.timer = QTimer()
        self.timer.timeout.connect(self.check_whea_events)

        self.trigger_form = TriggerSettingsForm()
        self.trigger_form.save_callback = self.update_trigger_config

        self.setup_ui()
        self.setup_tray()

        self.monitor_start_time = datetime.now()
        self.last_error_count = 0

        self.show_notification()

    def show_notification(self):
        """Простая функция для показа уведомления о сворачивании приложения в трей."""
        self.tray_icon.showMessage(
            "WHEA Monitor",
            "Приложение свернуто в трей. Чтобы открыть, нажмите на иконку.",
            QSystemTrayIcon.MessageIcon.Information,
            3000
        )

    def setup_ui(self):
        self.setWindowTitle("Монитор WHEA")
        icon_path = resource_path("icon.ico")
        self.icon = QIcon(icon_path) if os.path.exists(icon_path) else QIcon()
        self.setWindowIcon(self.icon)
        self.setFixedSize(550, 380)  # Ширина прежняя, не меняем

        self.setStyleSheet("""
            QWidget {
                background-color: #1e1f26;
                color: #e0e0e0;
                font-family: 'Segoe UI';
                font-size: 14px;
            }
            QLabel { color: #F0F0F0; }
            QLineEdit {
                background-color: #2c2d35;
                border: 1px solid #444;
                border-radius: 6px;
                padding: 4px 8px;
                color: #ffffff;
            }
            QPushButton {
                background-color: #3f51b5;
                border-radius: 6px;
                color: white;
                padding: 4px 10px;
            }
            QPushButton:hover { background-color: #303f9f; }
            QCheckBox { color: #F0F0F0; }
        """)

        self.interval_label = QLabel("Интервал проверки (сек)", self)
        self.interval_label.setGeometry(20, 20, 170, 24)

        self.interval_input = QLineEdit("30", self)
        self.interval_input.setGeometry(200, 18, 60, 24)
        self.interval_input.setValidator(QIntValidator(1, 3600))

        self.start_button = QPushButton("Старт", self)
        self.start_button.setGeometry(280, 16, 80, 28)
        self.start_button.clicked.connect(self.start_monitor)

        self.stop_button = QPushButton("Стоп", self)
        self.stop_button.setGeometry(370, 16, 80, 28)
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_monitor)

        self.log_output = QTextEdit(self)
        self.log_output.setGeometry(20, 60, 510, 250)  # Старая ширина 510

        self.trigger_button = QPushButton("⚡ Настроить триггер", self)
        self.trigger_button.setGeometry(20, 320, 180, 30)
        self.trigger_button.clicked.connect(lambda: self.trigger_form.exec())

        self.tools_button = QPushButton("WHEA Tools", self)
        self.tools_button.setGeometry(220, 320, 130, 30)
        self.tools_button.clicked.connect(self.run_whea_tools)

    def setup_tray(self):
        self.tray_icon = QSystemTrayIcon(self.icon, self)
        tray_menu = QMenu()

        title_action = QAction("WHEA Monitor", self)
        font = title_action.font()
        font.setBold(True)
        title_action.setFont(font)
        title_action.setEnabled(True)
        title_action.triggered.connect(self.show_normal)
        tray_menu.addAction(title_action)
        tray_menu.addSeparator()

        self.act_start = QAction("Запустить", self)
        self.act_start.triggered.connect(self.start_monitor)
        tray_menu.addAction(self.act_start)

        self.act_stop = QAction("Остановить", self)
        self.act_stop.setEnabled(False)
        self.act_stop.triggered.connect(self.stop_monitor)
        tray_menu.addAction(self.act_stop)
        tray_menu.addSeparator()

        quit_action = QAction("Закрыть WHEA Monitor", self)
        quit_action.triggered.connect(self.exit_app)
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_icon_activated)
        self.tray_icon.show()
        self.update_tray_actions()

    def on_tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.show_normal()

    def show_normal(self):
        self.show()
        self.raise_()
        self.activateWindow()

    def closeEvent(self, event):
        event.ignore()
        self.hide()

    def update_tray_actions(self):
        running = self.timer.isActive()
        self.act_start.setEnabled(not running)
        self.act_stop.setEnabled(running)

    def start_monitor(self):
        try:
            interval = int(self.interval_input.text())
            if interval < 1 or interval > 3600:
                raise ValueError()
        except ValueError:
            self.log_output.append(f"[{datetime.now().strftime('%H:%M:%S')}] Ошибка: интервал должен быть от 1 до 3600")
            write_log("Ошибка запуска мониторинга: неверный интервал.")
            return

        if interval < 5:
            self.log_output.append(f"[{datetime.now().strftime('%H:%M:%S')}] Внимание: интервал ниже 5 секунд может вызывать нагрузку на CPU")

        self.interval_input.setDisabled(True)
        self.log_output.append(f"[{datetime.now().strftime('%H:%M:%S')}] Мониторинг WHEA запущен")
        write_log(f"Мониторинг WHEA запущен с интервалом {interval} секунд")
        self.monitor_start_time = datetime.now()
        self.timer.start(interval * 1000)
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.update_tray_actions()
        self.last_error_count = 0

    def stop_monitor(self):
        self.timer.stop()
        self.log_output.append(f"[{datetime.now().strftime('%H:%M:%S')}] Мониторинг WHEA остановлен")
        write_log("Мониторинг WHEA остановлен")
        self.interval_input.setDisabled(False)
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.update_tray_actions()
        self.last_error_count = 0

    def exit_app(self):
        self.tray_icon.hide()
        QApplication.quit()

    def check_whea_events(self):
        server = 'localhost'
        log_type = 'System'
        flags = win32evtlog.EVENTLOG_BACKWARDS_READ | win32evtlog.EVENTLOG_SEQUENTIAL_READ

        try:
            hand = win32evtlog.OpenEventLog(server, log_type)
            write_log(f"Открыт журнал событий Windows: {log_type} на сервере {server}")
        except Exception as e:
            err = f"Ошибка открытия журнала событий: {e}"
            self.log_output.append(f"[{datetime.now().strftime('%H:%M:%S')}] {err}")
            write_log(err)
            return

        count = 0
        found_event_ids = set()
        sample_events_info = []

        try:
            events = win32evtlog.ReadEventLog(hand, flags, 0)
        except Exception as e:
            err = f"Ошибка чтения журнала событий: {e}"
            self.log_output.append(f"[{datetime.now().strftime('%H:%M:%S')}] {err}")
            write_log(err)
            return

        if not events:
            write_log("Журнал событий пуст")
            return

        for ev in events[:5]:
            sample_events_info.append(event_to_dict(ev))

        for event in events:
            try:
                event_time = datetime.fromtimestamp(pywintypes.Time(event.TimeGenerated).timestamp())
            except Exception:
                continue
            if event_time < self.monitor_start_time:
                continue
            event_id = event.EventID & 0xFFFF
            if event_id not in self.WHEA_EVENT_IDS:
                continue
            count += 1
            found_event_ids.add(event_id)

        write_log(f"Структура первых прочитанных событий (макс 5): {json.dumps(sample_events_info, ensure_ascii=False, indent=2)}")
        write_log(f"Всего найдено ошибок/предупреждений WHEA: {count}, Коды ошибок: {sorted(found_event_ids)}")

        timestamp = datetime.now().strftime('%H:%M:%S')
        if count > 0 and count != self.last_error_count:
            codes_str = ', '.join(str(eid) for eid in sorted(found_event_ids))
            msg = f"[{timestamp}] Найдена ошибка WHEA ({count}). Коды ошибок: {codes_str}"
            self.log_output.append(msg)
            self.show_system_notification("WHEA Monitor", msg)
            write_log(msg)
            # Логируем в отдельный файл ошибок с точной датой и временем и кодом ошибки
            write_error_log(msg)
            self.handle_trigger()
            self.last_error_count = count
        elif count == 0 and self.last_error_count != 0:
            self.last_error_count = 0
            write_log(f"[{timestamp}] Ошибок WHEA не найдено, счетчик ошибок сброшен.")

    def handle_trigger(self):
        cfg = getattr(self, "trigger_config", {})
        if not cfg:
            return

        if cfg.get("message_enabled", False):
            msg = cfg["message_text"].strip() if cfg.get("message_custom_enabled", False) and cfg.get("message_text", "").strip() else "Обнаружена ошибка WHEA"
            show_messagebox(msg)
            write_log(f"Отправлено сообщение: {msg}")

        if cfg.get("audio_enabled", False):
            idx = cfg.get("audio_selected_index")
            if idx in [0, 1, 2]:
                path = self.trigger_form.sounds[idx][1]
                if os.path.exists(path):
                    winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC)
                    write_log(f"Воспроизведён звук: {path}")
                    return
            winsound.MessageBeep(winsound.MB_OK)
            write_log("Воспроизведён стандартный звуковой сигнал")

        if cfg.get("execute_enabled", False):
            path = cfg.get("execute_path")
            args = cfg.get("execute_args", "")
            if path and os.path.exists(path):
                try:
                    if args.strip():
                        os.startfile(f'"{path}" {args}')
                    else:
                        os.startfile(path)
                    winsound.MessageBeep(winsound.MB_OK)
                    write_log(f"Запущена программа: {path} с аргументами: {args}")
                except Exception as e:
                    err = f"Ошибка запуска программы: {e}"
                    self.log_output.append(f"[{datetime.now().strftime('%H:%M:%S')}] {err}")
                    write_log(err)
            else:
                write_log("Путь к программе не задан или не существует")

    def update_trigger_config(self, config):
        self.trigger_config = config
        write_log(f"Обновлена конфигурация триггера: {json.dumps(config, ensure_ascii=False)}")
        # Сохраняем конфигурацию триггера в файл
        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            write_log(f"Ошибка сохранения конфигурации триггера: {e}")

    def run_whea_tools(self):
        bat_code = r"""@echo off
chcp 65001 >nul

:: Проверка прав администратора
>nul 2>&1 "%SYSTEMROOT%\system32\cacls.exe" "%SYSTEMROOT%\system32\config\system"
if '%errorlevel%' NEQ '0' (
    echo Admin rights required. Restarting as admin...
    powershell -Command "Start-Process -Verb runAs -FilePath '%~f0'"
    exit /b
)

:main_loop
cls
echo ┌─────┐ ┌─────┐ ┌─────┐  ┌───────────────────────────────────────────────────┐
echo │ ┌───┘ │ ┌─┐ │ │ ┌───┘  │ Forgotten Private Coalition                       │
echo │ └───┐ │ └─┘ │ │ │      │ WHEA Trigger Tools                                │
echo │ ┌───┘ │ ┌───┘ │ │      -│ Private version                                   │
echo │ │     │ │     │ └───┐  │ License CC BY 4.0                                 │
echo └─┘     └─┘     └─────┘  └───────────────────────────────────────────────────┘
echo.
echo Available WHEA EventIDs and meanings:
echo  17 - General hardware error event
echo  18 - Machine Check Exception (MCE)
echo  19 - Corrected Machine Check error
echo  20 - PCI Express error
echo  41 - Detailed WHEA error report
echo  45 - Corrected memory error
echo  46 - Corrected processor error
echo  47 - Corrected PCI Express error
echo.
echo Commands:
echo  ex - Exit program
echo  el - Open Windows Event Viewer / System log
echo  ec - Clear all errors from TestWHEA source
echo.

if defined last_message (
    echo %last_message%
    echo.
    set "last_message="
)

set /p input=Enter "EventID Level" (Level: 1=Warning, 2=Error) or command (ex, el, ec): 

:: Command checks
if /i "%input%"=="ex" (
    exit /b
)
if /i "%input%"=="el" (
    start eventvwr.msc /s:"System"
    set last_message=Windows System event log opened.
    goto main_loop
)
if /i "%input%"=="ec" (
    echo Clearing all errors from TestWHEA source...
    wevtutil.exe cl System
    set last_message=System log cleared.
    goto main_loop
)

:: Process EventID and Level
for /f "tokens=1,2" %%a in ("%input%") do (
    set "code=%%a"
    set "level=%%b"
)

if not defined code (
    set last_message=Invalid input. Try again.
    goto main_loop
)
if not defined level (
    set last_message=Invalid input. Try again.
    goto main_loop
)

set executed=0

for %%E in (17 18 19 20 41 45 46 47) do (
    if "%code%"=="%%E" (
        if "%level%"=="1" (
            eventcreate /T WARNING /ID %%E /L SYSTEM /SO TestWHEA /D "Test warning WHEA (EventID %%E)"
            set executed=1
        ) else if "%level%"=="2" (
            eventcreate /T ERROR /ID %%E /L SYSTEM /SO TestWHEA /D "Test error WHEA (EventID %%E)"
            set executed=1
        )
    )
)

if "%executed%"=="1" (
    set last_message=Operation successful.
    goto main_loop
) else (
    set last_message=Invalid input or unsupported EventID/Level. Try again.
    goto main_loop
)
"""
        try:
            with tempfile.NamedTemporaryFile("w", delete=False, suffix=".bat", encoding="utf-8") as tmpfile:
                tmpfile.write(bat_code)
                tmp_path = tmpfile.name
            subprocess.Popen(
                ["cmd.exe", "/c", tmp_path],
                creationflags=subprocess.CREATE_NO_WINDOW
            )
        except Exception as e:
            write_log(f"Error launching WHEA Tools: {e}")

    def show_system_notification(self, title: str, message: str):
        """Показываем системное уведомление (push)"""
        if self.tray_icon.isVisible():
            self.tray_icon.showMessage(title, message, QSystemTrayIcon.MessageIcon.Warning, 5000)

    def keyPressEvent(self, event):
        # CTRL+X открывает папку %appdata%\Forgotten
        if event.key() == Qt.Key.Key_X and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            forgotten_path = os.path.join(os.getenv("APPDATA"), "Forgotten")
            if os.path.exists(forgotten_path):
                subprocess.Popen(f'explorer "{forgotten_path}"')
            event.accept()
        else:
            super().keyPressEvent(event)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = WheaMonitorApp()

    sys.exit(app.exec())
