#!/usr/bin/env python3

import configparser
import sys
import os
import subprocess
import re
from PyQt5.QtCore import QTimer, pyqtSignal, Qt
from PyQt5.QtWidgets import QApplication, QLabel, QWidget, QVBoxLayout, QGridLayout, QTextEdit, QPushButton, QVBoxLayout, QScrollArea, QHBoxLayout, QSpacerItem, QSizePolicy
from functools import partial
from datetime import datetime, timedelta
from collections import deque
from PyQt5.QtCore import Qt, QCoreApplication, QThread
from PyQt5.QtGui import QPainter, QColor, QIcon
import base64

# Styling
HEADER_STYLE              = "font-size: 26px; text-align:center;font-weight: bold;color: #00cc00;background-color: #121;padding-bottom:4px;margin-bottom:0px;"
HEADER_STYLE_BACKGROUND   = "font-size: 26px; text-align:center;font-weight: bold;color: #006600;background-color: #111;padding-bottom:4px;margin-bottom:0px;"
CONFIG_LABEL_STYLE        = "font-size: 12px;text-align:left;background:#262;padding:2px;font-weight:bold"
SECTION_LABEL_STYLE       = "margin-top:30px;font-size: 12px;font-weight:bold;text-align:left;background-color:#000;padding:3px;margin:0px;"
FILE_CONTENTS_FIELD_STYLE = "background-color: #444; color: #fff;font-size:11px;"
INPUT_FIELD_STYLE         = "background-color: #ccc; color: #333;font-size:12px;padding:3px"
SUBMIT_BUTTON_STYLE       = "background-color: #050;color:#8d8;font-size:10px;padding: 5px 0px;margin: 0px 50px;"
DISPLAY_FIELD_STYLE       = "background-color: #444; color: #fff;font-size:11px;"
STATUS_FIELD_STYLE        = "background-color: #121; color: #00cc00"
HOVER_BUTTON_STYLE        = "font-size: 14px;padding-top: 3px; padding-bottom: 3px; margin:0px;padding-left:3px; margin-top: -3px; margin-bottom: -3px;text-align: left;background: #666"
SCROLL_AREA_STYLE         = "QScrollArea {border: 1px solid #666;padding:0px;margin: 0px;} QScrollBar {border: none;}"
OUTPUT_STYLE              = "QScrollArea {border: 1px solid #666;padding:0px;margin: 0px;} QScrollBar {border: none;}"

# Settings
STATUS_FIELD_HEIGHT           = 90
INPUT_FIELD_HEIGHT            = 35
CUSTOM_TEXT_EDIT_HEIGHT       = 35
CUSTOM_TEXT_EDIT_FOCUS_HEIGHT = 100
SCROLL_AREA_FIXED_HEIGHT      = 100
BACKGROUNDED_LABEL_SIZE       = 30

DEFAULT_CONFIG = """
# CMD_PAL Configuration File
#
# This file contains the configuration settings for CMD_PAL.
# Each section represents a different widget in the CMD_PAL interface.
#
# Available options for each section:
#   type (required): The type of widget to display. Options are 'log', 'parse_command', and 'display'.
#
#   value (required): The value associated with the widget type.
#     - For 'log': The file path for the log file (e.g., '~/my_log.txt').
#     - For 'parse_command': The command to be executed and parsed (e.g., 'ls -la').
#     - For 'display': The command to be executed and displayed (e.g., 'date').
#
#   interval (required): The time interval (in seconds) between updates for the widget.
#
# Additional options specific to 'parse_command' type:
#   clean (optional, default=False): If set to True, the widget will remove old entries before updating.
#   split (optional, default=False): If set to True, the output of the command will be split by newline characters.
#   action (optional, default='insert'): The action to perform when a button is clicked.
#     - 'insert': Switches to the last app frontmost and inserts the text
#     - 'show': Shows the command in a terminal window (new or existing)
#     - 'run': Runs the command internally and displays the output in the bottom status field.
#
#   When using the parse_command type, you can assign custom labels to buttons with 
#   lines like "ls -lah ;: My ls" to create a [My ls] button.

# Default config assumes zsh shell but you can customize it to be whatever
[History]
type = parse_command
# history in zsh is stored like ": 1687218706:0;ls" so we cleanup.
value = tail -n 50 ~/.zsh_history | cut -d ";" -f2- -s
interval = 4
clean = True
split = True
action = show


[Clipboard]
type = parse_command
value = pbpaste
interval = 4
clean = False
split = False
action = insert

[Ruby Shell]
type = parse_command
value = tail -n 50 ~/.pry_history
interval = 4
clean = True
split = True
action = insert

[notes.txt]
type = log
value = ~/.cmd_pal/notes.txt
interval = 10

[Uptime]
type = display
value = uptime
interval = 10
"""

# Classes

class CommandThread(QThread):
    result_signal = pyqtSignal(str)

    def __init__(self, command, action):
        super().__init__()
        self.command = command
        self.action = action

    def run(self):
        result = execute_command_in_parent_terminal(self.command, self.action)
        self.result_signal.emit(result)

class CustomTextEdit(QTextEdit):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def focusInEvent(self, event):
        super().focusInEvent(event)
        self.setFixedHeight(CUSTOM_TEXT_EDIT_FOCUS_HEIGHT)  

    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        self.setFixedHeight(CUSTOM_TEXT_EDIT_HEIGHT)

class RotatedLabel(QLabel):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setPen(QColor(0,150,50))
        painter.translate(self.width() / 2, self.height() / 2)
        painter.rotate(90)
        painter.drawText(-int(self.height() / 2), -int(self.width() / 2), self.height(), self.width(), Qt.AlignCenter, self.text())
        painter.end()

class HoverButton(QPushButton):
    mouse_hover = pyqtSignal(bool)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def enterEvent(self, event):
        self.mouse_hover.emit(True)

    def leaveEvent(self, event):
        self.mouse_hover.emit(False)

# Functions
def handle_focus_changed(old_widget, new_widget):
    if new_widget is None:
        # hiding
        backgrounded_label.show()
        header.hide()
        status_text_field.hide()
        #window.setFixedWidth(len(configs) * 100)
        window.original_pos = window.pos()
        window.move(-(window.width() - BACKGROUNDED_LABEL_SIZE), window.y())
        header.setStyleSheet(HEADER_STYLE_BACKGROUND)
    else:
        # showing
        backgrounded_label.hide()
        header.show()
        status_text_field.show()
        window.move(window.original_pos)
        header.setStyleSheet(HEADER_STYLE)

def load_config(config_path):
    config = configparser.ConfigParser()
    config.read(config_path)
    return config

def extract_comment(line):
    match = re.search(r';\:\s*(.*)', line)
    if match:

        comment = match.group(1)
        return comment
    else:
        return None
def create_update_output_lambda(section, output_layout, scroll_area, config):
    return lambda: update_output(section, output_layout, scroll_area, config)

def create_start_process_lambda(section, output_layout, scroll_area, config):
    return lambda: start_process(section, output_layout, scroll_area, config)

def clear_section_buttons(output_layout):
    for i in reversed(range(output_layout.count())):
        item = output_layout.itemAt(i)
        if item is not None:
            widget = item.widget()
            if isinstance(widget, HoverButton):
                output_layout.removeWidget(widget)
                widget.deleteLater()

def remove_existing_buttons(output_layout, content):
    for i in range(output_layout.count()):
        item = output_layout.itemAt(i)
        if item is not None:
            widget = item.widget()
            if isinstance(widget, HoverButton) and widget.text() == content:
                output_layout.removeWidget(widget)

command_threads = []

def execute_and_display_result(command, action):
    if action == "run":
        command_thread = CommandThread(command, action)
        command_thread.result_signal.connect(status_text_field.append)
        command_thread.finished.connect(lambda: command_threads.remove(command_thread))
        command_threads.append(command_thread)
        command_thread.start()
    else:
        execute_command_in_parent_terminal(command, action)
    
    
def update_output(section, output_layout, scroll_area, config):
    if config.getboolean(section, 'clean', fallback=False):
        clear_section_buttons(output_layout)
    result = os.popen(config.get(section, 'value')).read()

    if config.getboolean(section, 'split', fallback=False):
        items = reversed(result.split('\n'))
    else:
        items = [result]

    items = list(dict.fromkeys(items))

    if config.get(section, 'type') == 'display':
        output_layout.setPlainText(items[0])
    else:
        new_items = []
        for item in items:
            if not item.strip():
                continue  # Skip the current iteration and move to the next item
            title = extract_comment(item)
            if title:
                display_text = title[:100] + "..." if len(title) > 100 else title
            else:
                display_text = item[:100] + "..." if len(item) > 100 else item
            display_text = display_text.replace("\n", "  ")
            button = HoverButton(display_text, window)
            button.setStyleSheet(HOVER_BUTTON_STYLE)
            action = config.get(section, 'action', fallback='insert')
            button.mouse_hover.connect(partial(update_text_field, text=item))
            button.clicked.connect(partial(execute_and_display_result, command=item, action=action))  # Add this line
            new_items.append(button)

        for item in new_items:
            remove_existing_buttons(output_layout, item.text())
            output_layout.addWidget(item)

        if scroll_area is not None:
            scroll_area.ensureWidgetVisible(output_layout.itemAt(output_layout.count() - 1).widget())

def start_process(section, output_layout, scroll_area, config):
    update_output(section, output_layout, scroll_area, config)

def setup_section_widgets(window):
    scroll_area = QScrollArea(window)
    scroll_area.setFixedHeight(SCROLL_AREA_FIXED_HEIGHT)
    scroll_area.setWidgetResizable(True)
    scroll_area.setStyleSheet(SCROLL_AREA_STYLE)
    scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    scroll_area.verticalScrollBar().valueChanged.connect(interacted)
    output_widget = QWidget()
    output_layout = QVBoxLayout()
    output_layout.setAlignment(Qt.AlignTop)
    output_widget.setLayout(output_layout)
    output_widget.setStyleSheet(OUTPUT_STYLE)
    scroll_area.setWidget(output_widget)

    return scroll_area, output_layout

def update_text_field(hover, text):
    if hover:
        status_text_field.clear()
        status_text_field.setText(text)
        interacted()

def update_file_contents(section, file_contents_field, config):
    file_path = os.path.expanduser(config.get(section, 'value'))
    with open(file_path, 'a') as file:
        pass
    with open(file_path, 'r') as file:
        file_contents = file.read()
    file_contents_field.setPlainText(file_contents)
    file_contents_field.verticalScrollBar().setValue(file_contents_field.verticalScrollBar().maximum())

def handle_timer(section, output_layout, scroll_area, config, timer):
    if should_reload():
        start_process(section, output_layout, scroll_area, config)
        timer.start(config.getint(section, 'interval') * 1000)

def handle_file_timer(section, file_contents_field, config):
    if should_reload():
        update_file_contents(section, file_contents_field, config)

def append_to_file(section, input_field, file_contents_field, config):
    file_path = os.path.expanduser(config.get(section, 'value'))
    timestamp = datetime.now().strftime("-- %m/%d/%y %I:%M%p --\n\n")
    with open(file_path, 'a') as file:
        file.write(timestamp + input_field.toPlainText() + '\n')
    input_field.clear()
    QTimer.singleShot(0, partial(update_file_contents, section, file_contents_field, config))

scrollbar_events = deque(maxlen=7)

# interactions like scrolling or hovering on a button should pause all updates for a few seconds
def interacted():
    global scrollbar_events
    scrollbar_events.append(datetime.now())

    # Check if there are more than 5 scroll events in the last second
    recent_events = [event for event in scrollbar_events if datetime.now() - event <= timedelta(seconds=2)]
    if len(recent_events) > 4:
        global next_reload_time
        next_reload_time = datetime.now() + reload_delay

def should_reload():
    global next_reload_time
    result = datetime.now() >= next_reload_time
    return result

def execute_command_in_parent_terminal(command, action="insert"):
    if action == "insert":
        encoded_command = base64.b64encode(command.encode()).decode()
        applescript = f'''
        tell application "System Events"
            set frontApp to name of first application process whose frontmost is true
        end tell
        delay 0.1
        tell application "System Events"
            key down command
            keystroke tab
            key up command
            delay 0.1
            set decoded_command to do shell script "echo '{encoded_command}' | base64 --decode"
            keystroke decoded_command
        end tell
        '''
        subprocess.run(['osascript', '-e', applescript], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return "Done!"
    elif action == "show":
        applescript = f'tell application "Terminal" to do script "{command}" in front window'
        subprocess.run(['osascript', '-e', applescript], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return "Done!"
    elif action == "run":
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, text=True)
        return result.stdout.strip()

if __name__ == "__main__":
    default_config_path = os.path.expanduser("~/.cmd_pal/config")

    if not os.path.exists(default_config_path):
        os.makedirs(os.path.dirname(default_config_path), exist_ok=True)
        with open(default_config_path, "w") as config_file:
            config_file.write(DEFAULT_CONFIG)

    configs = [load_config(default_config_path)]

    for i in range(1, len(sys.argv)):
        if sys.argv[i] == "-c":
            config_path = sys.argv[i + 1]
            configs.append(load_config(config_path))

    app = QApplication([])
    app.setWindowIcon(QIcon('icon.png'))
    app.setApplicationName("CMD_PAL")

    app.focusChanged.connect(handle_focus_changed)
    app.setStyleSheet("QWidget {background-color: #333}")

    window = QWidget()

    window.setWindowTitle('CMD_PAL')
    window.setGeometry(100, 100, 20 * len(configs), 400)
    window.setWindowFlags(Qt.WindowStaysOnTopHint)

    main_layout = QVBoxLayout()
    main_layout.setContentsMargins(0,0,0,0)
    header = QLabel("CMD_PAL  v1.0", window)
    header.setStyleSheet(HEADER_STYLE)
    main_layout.addWidget(header)

    main_layout.setStretch(0, 0)

    config_sections_layout = QHBoxLayout()
    config_sections_layout.setContentsMargins(0,0,0,0)
    config_sections_layout.setSpacing(2)
    main_layout.setSpacing(0)
    main_layout.addLayout(config_sections_layout)

    reload_delay = timedelta(seconds=10)
    next_reload_time = datetime.now()

    for config_index, config in enumerate(configs):
        config_layout = QVBoxLayout()
        config_layout.setSpacing(5) # sets section spacing
        config_label = QLabel(os.path.abspath(default_config_path), window)
        config_label.setWordWrap(True)
        config_label.setStyleSheet(CONFIG_LABEL_STYLE)

        config_layout.addWidget(config_label)

        for section in config.sections():

            current_section = section
            section_type = config.get(section, 'type')
            action = config.get(section, 'action', fallback=None)
            if action:
                section_label = QLabel(section + " ({})".format(action), window)
            else:
                section_label = QLabel(section, window)
            section_label.setStyleSheet(SECTION_LABEL_STYLE)
            section_label.setWordWrap(True)
            spacer_item = QSpacerItem(0, 10, QSizePolicy.Minimum, QSizePolicy.Fixed)
            config_layout.addItem(spacer_item)
            config_layout.addWidget(section_label)

           

            if section_type == 'log':
                file_contents_field = QTextEdit(window)
                file_contents_field.setReadOnly(True)
                file_contents_field.setStyleSheet(FILE_CONTENTS_FIELD_STYLE)
                file_contents_field.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
                file_contents_field.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
                config_layout.addWidget(file_contents_field)

                input_field = CustomTextEdit(window)
                input_field.setFixedHeight(CUSTOM_TEXT_EDIT_HEIGHT)
                input_field.setStyleSheet(INPUT_FIELD_STYLE)
                config_layout.addWidget(input_field)
                file_contents_field.verticalScrollBar().valueChanged.connect(interacted)
                spacer_item = QSpacerItem(0, 5, QSizePolicy.Minimum, QSizePolicy.Fixed)
                config_layout.addItem(spacer_item)
                submit_button = QPushButton("ADD", window)
                submit_button.setStyleSheet(SUBMIT_BUTTON_STYLE)
                submit_button.clicked.connect(partial(append_to_file, section, input_field, file_contents_field, config))
                config_layout.addWidget(submit_button)
                QTimer.singleShot(0, partial(update_file_contents, section, file_contents_field, config))
                timer = QTimer(window)
                timer.timeout.connect(partial(handle_file_timer, section, file_contents_field, config))
                timer.start(config.getint(section, 'interval') * 1000)

            elif section_type == 'parse_command' and config.get(section, 'value'):
                scroll_area, output_layout = setup_section_widgets(window)
                config_layout.addWidget(scroll_area)
                QTimer.singleShot(0, partial(start_process, section, output_layout, scroll_area, config))
                timer = QTimer(window)
                timer = QTimer(window)
                timer.timeout.connect(partial(handle_timer, section, output_layout, scroll_area, config, timer))
                timer.start(config.getint(section, 'interval') * 1000)

            elif section_type == 'display' and config.get(section, 'value'):
                display_field = QTextEdit(window)
                display_field.setReadOnly(True)
                display_field.setStyleSheet(DISPLAY_FIELD_STYLE)
                display_field.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
                display_field.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
                display_field.verticalScrollBar().valueChanged.connect(interacted)
                config_layout.addWidget(display_field)
                QTimer.singleShot(0, partial(update_output, section, display_field, None, config))
                timer = QTimer(window)
                timer.timeout.connect(partial(update_output, section, display_field, None, config))
                timer.start(config.getint(section, 'interval') * 1000)

        config_sections_layout.addLayout(config_layout)

    backgrounded_label = RotatedLabel("CMD_PAL", window)
    backgrounded_label.setFixedWidth(BACKGROUNDED_LABEL_SIZE)
    backgrounded_label.setStyleSheet(HEADER_STYLE)
    config_sections_layout.addWidget(backgrounded_label)

    spacer = QSpacerItem(0, 0, QSizePolicy.Minimum, QSizePolicy.Expanding)
    main_layout.addItem(spacer)

    status_text_field = QTextEdit(window)
    status_text_field.setFixedHeight(STATUS_FIELD_HEIGHT)
    status_text_field.setStyleSheet(STATUS_FIELD_STYLE)
    main_layout.addWidget(status_text_field)

    window.setWindowTitle("CMD_PAL")
    window.setLayout(main_layout)
    window.setGeometry(0, 100, 300 * len(configs), 1000)
    window.show()
    window.original_pos = window.pos()

    try:
      sys.exit(app.exec())
    except KeyboardInterrupt:
      print("\nExiting...")
      sys.exit(0)