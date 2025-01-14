# Django Code Analysis Tool

A powerful tool for analyzing Django projects, monitoring code changes, and generating comprehensive reports about your codebase. This tool is designed to help developers understand their Django projects better by providing insights into code structure, relationships between files, and tracking changes over time.

## Features

- **Token-Aware Analysis**: Intelligently analyzes your codebase while respecting token limits
- **Real-Time Monitoring**: Watches for file changes and automatically generates updated reports
- **Smart File Selection**: Prioritizes recently modified files and their related components
- **Context-Aware Analysis**: Understands relationships between Django components (views, models, templates, etc.)
- **Comprehensive Reporting**: Generates detailed reports including:
  - Project structure overview
  - File contents with syntax highlighting
  - Token usage statistics
  - File relationships and dependencies
  - Recent modifications tracking

## Installation

```bash
# Clone the repository
git clone [your-repo-url]
cd [repo-name]

# Install required dependencies
pip install watchdog
```

## Usage

The tool consists of two main components:

### 1. Code Analyzer (dj_context_print.py)

Run a one-time analysis of your Django project:

```bash
python dj_context_print.py --dir ./your_django_project --report
```

Options:
- `--dir`, `-d`: Specify the directory to analyze
- `--report`, `-r`: Generate a complete project report

### 2. File Watcher (watcher.py)

Monitor your project for changes and automatically generate updated reports:

```bash
python watcher.py
```

The watcher will:
- Monitor relevant Django files (.py, .html, .js, .css)
- Generate an initial report
- Create new reports when changes are detected (with a configurable cooldown period)

## Configuration

The tool comes with sensible defaults but can be customized:

- **Token Limits**: Adjust `MAX_TOKENS` and `CHARS_PER_TOKEN` in `TokenAwareAnalyzer`
- **Excluded Directories**: Modify `EXCLUDED_DIRECTORIES` to skip specific folders
- **File Patterns**: Update `DJANGO_PATTERNS` to change which files are analyzed
- **Cooldown Period**: Adjust the minimum time between analyses in `DjangoWatcher`

## Output

Reports are generated in the `print_codebase` directory and include:
- Overall project statistics
- JSON representation of project structure
- File contents with metadata
- List of excluded files
- Relationship analysis between components

## How It Works

1. **File Discovery**: The tool scans your Django project, identifying relevant files while respecting exclusion patterns.

2. **Smart Selection**: Files are prioritized based on:
   - Recent modifications
   - File type importance (models, views, etc.)
   - Relationships with other files
   - Token budget constraints

3. **Context Analysis**: The tool understands Django-specific relationships:
   - View-Template connections
   - Model-View dependencies
   - Form-View relationships
   - URL patterns

4. **Report Generation**: Comprehensive reports are created, combining structural analysis with content preservation.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Authors

Giuseppe Birardi
