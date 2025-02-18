# Wiki-Lookup
A simple Wikipedia lookup tool using PyQt6.

A lightweight Wikipedia lookup tool that provides instant summaries when a word or phrase is selected. Inspired by the macOS lookup feature.

## Features
- Automatically detects selected text and fetches Wikipedia summaries.
- Displays extracted content in a clean, floating pop-up window.
- Fetches relevant images from Wikipedia (if available).
- Closes automatically after inactivity.
- Works in the background, monitoring clipboard changes.

## Technologies Used
- Python
- PyQt6 for GUI
- Requests for Wikipedia API calls
- LRU cache for performance optimization

## Installation
### Prerequisites
Ensure you have Python installed. Then, install the dependencies:
```sh
pip install pyqt6 requests pyperclip
```

### Running the Application
```sh
python lookup.py
```

## Usage
1. Copy any text in any application.
2. The tool automatically fetches the Wikipedia summary and displays it.
3. Close the pop-up manually or wait for it to disappear after 10 seconds.


