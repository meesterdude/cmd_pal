# CMD_PAL

CMD_PAL is a powerful MacOS Command Pallete GUI that enhances your productivity by making it easier to work with commands, the clipboard, and text.

It is designed to be highly customizable via configuration and be easy to use.

![CMD_PAL Screenshot](cmd_pal_demo.mov)

## Features

- Display frequently used commands, append notes to files, command output
- Highly customizable through a simple configuration file
- Supports multiple configuration files (via `-c` option), each rendering as additional column 
- Automatically refreshes displayed information at specified intervals
- Execute commands directly from the interface with a single click
- Insert command output into the active terminal or application
- Show command output in a new or existing terminal window
- Preview commands and edit in-line with the inline preview before copying out
- organize frequently used commands into a dedicated text file for quick reuse

## Installation

CMD_PAL is available as a standalone application or a terminal app. You can choose the application approach that best suits your needs.

### Standalone Application

1. Download the latest release

2. Extract the downloaded archive to reveal the `dist` folder.

3. Inside the `dist` folder, you will find the cmd_pal.app application. Simply drag and drop it into your Applications folder.

4. Run CMD_PAL from your Applications folder.

### Terminal App

1. Clone the repository:

   ```
   git clone https://github.com/meesterdude/cmd_pal.git
   ```

2. Change to the `cmd_pal` directory:

   ```
   cd cmd_pal
   ```


4. Add the `cmd_pal` executable to a directory in your local executable path (e.g., `/usr/local/bin` or `~/bin`). You can create a symlink or copy the file directly:

   ```
   ln -s "$(pwd)/dist/cmd_pal" /usr/local/bin/cmd_pal
   ```

   or

   ```
   cp dist/cmd_pal /usr/local/bin/cmd_pal
   ```

5. Make sure the script is executable:

   ```
   chmod +x /usr/local/bin/cmd_pal
   ```

6. Run CMD_PAL from your terminal:

   ```
   cmd_pal
   ```

## Configuration

CMD_PAL uses a simple configuration file to define the sections and widgets displayed in the interface. The default configuration file is located at 
`~/.cmd_pal/config` and is created on start if not present. It is fully documented with the options.  You can create additional configuration files and load them by passing the `-c` flag followed by the file path when running CMD_PAL:

```
cmd_pal -c /path/to/your/config_file -c /different/path/project_config_file
```

### Configuration Options

Each section in the configuration file represents a different widget in the CMD_PAL interface. The available options for each section are:

- `type` (required): The type of widget to display. Options are 'log', 'parse_command', and 'display'.
- `value` (required): The value associated with the widget type.
  - For 'log': The file path for the log file (e.g., '~/my_log.txt').
  - For 'parse_command': The command to be executed and parsed (e.g., 'ls -la').
  - For 'display': The command to be executed and displayed (e.g., 'date').
- `interval` (required): The time interval (in seconds) between updates for the widget.
- `clean` (optional, default=False): If set to True, the widget will remove old entries before updating.
- `split` (optional, default=False): If set to True, the output of the command will be split by newline characters.
- `action` (optional, default='insert'): The action to perform when a button is clicked.
  - 'insert': Switches to the last app frontmost and inserts the text
  - 'show': Shows the command in a terminal window (new or existing)
  - 'run': Runs the command internally and displays the output in the bottom status field.

When using the `parse_command` type, you can assign custom labels to buttons with lines like "ls -lah ;: My ls" to create a [My ls] button.

## Contributing

We welcome contributions to CMD_PAL! If you have a feature request, bug report, or want to contribute code, please open an issue or submit a pull request on 
GitHub.

## License

CMD_PAL is released under the MIT License. 
