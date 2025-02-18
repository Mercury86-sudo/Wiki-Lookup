from PyQt6.QtWidgets import QApplication, QMainWindow, QTextEdit, QVBoxLayout, QHBoxLayout, QWidget, QProgressBar, QLabel, QToolBar
from PyQt6.QtGui import QAction, QPixmap, QCursor, QClipboard
from PyQt6.QtCore import Qt, QTimer, QSize
import sys
import requests
import pyperclip
from functools import lru_cache
import time

class LoadingOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)  # Infinite loading animation
        layout.addWidget(self.progress)
        self.setStyleSheet("""
            QWidget {
                background-color: rgba(255, 255, 255, 200);
                border-radius: 5px;
            }
            QProgressBar {
                border: 2px solid grey;
                border-radius: 5px;
                text-align: center;
            }
        """)

class RichTextEdit(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.popup = None
        self.setAcceptRichText(True)
        self.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse | 
            Qt.TextInteractionFlag.LinksAccessibleByMouse |
            Qt.TextInteractionFlag.TextEditable
        )
        self.setReadOnly(True)  # Make it read-only while still allowing selection
        
        # Set a minimum width for the text area
        self.setMinimumWidth(300)

class ImageLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMaximumSize(QSize(200, 200))  # Slightly smaller max size
        self.setMinimumSize(QSize(150, 100))  # Minimum size to prevent collapse
        self.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.setStyleSheet("""
            QLabel {
                background-color: #f5f5f5;
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 4px;
                margin: 4px;
            }
        """)

    def setImage(self, image_url):
        try:
            headers = {
                'User-Agent': 'WikiLookupTool/1.0 (mailto:your.email@example.com) Python/3.8'
            }
            response = requests.get(image_url, headers=headers, timeout=5)
            response.raise_for_status()
            image_data = response.content
            pixmap = QPixmap()
            pixmap.loadFromData(image_data)
            
            # Scale the image to fit within max dimensions while preserving aspect ratio
            scaled_pixmap = pixmap.scaled(
                self.maximumSize(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.setPixmap(scaled_pixmap)
        except Exception as e:
            print(f"Error loading image: {str(e)}")
            self.setText("Image loading failed")

class LookupWindow(QMainWindow):
    def __init__(self, text="", parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint)
        self._destroyed = False
        
        # Create central widget with horizontal layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setSpacing(10)  # Add some space between text and image
        
        # Create text view
        self.text_view = RichTextEdit()
        main_layout.addWidget(self.text_view, stretch=1)  # Text gets more space
        
        # Create image label
        self.image_label = ImageLabel()
        main_layout.addWidget(self.image_label)
        self.image_label.hide()  # Initially hidden until we have an image
        
        # Set window size - wider to accommodate side-by-side layout
        self.setGeometry(0, 0, 550, 300)

        # Create loading overlay
        self.loading_overlay = LoadingOverlay(self.text_view)
        self.loading_overlay.hide()
        
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        
        # Fetch content
        self.wiki_data = self.fetch_wikipedia(text)
        self.setWindowTitle(self.wiki_data['title'])
        self.load_content()
        
        self.ensure_visible_position()
        
        # Add a close timer
        self.close_timer = QTimer(self)
        self.close_timer.setSingleShot(True)
        self.close_timer.timeout.connect(self.close)
        self.close_timer.start(10000)  # Close after 10 seconds of inactivity

    def closeEvent(self, event):
        self._destroyed = True
        super().closeEvent(event)

    def is_destroyed(self):
        return bool(self._destroyed)

    def ensure_visible_position(self):
        cursor = QCursor.pos()
        screen = QApplication.primaryScreen().geometry()
        
        pos_x = min(cursor.x() + 20, screen.width() - self.width())
        pos_y = min(cursor.y() + 20, screen.height() - self.height())
        
        if pos_y + self.height() > screen.height():
            pos_y = max(0, cursor.y() - self.height() - 20)
            
        if pos_x + self.width() > screen.width():
            pos_x = max(0, cursor.x() - self.width() - 20)
            
        self.move(pos_x, pos_y)

    def show_loading(self):
        self.loading_overlay.setGeometry(self.text_view.rect())
        self.loading_overlay.show()

    def hide_loading(self):
        self.loading_overlay.hide()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.loading_overlay.setGeometry(self.text_view.rect())

    @lru_cache(maxsize=100)
    def fetch_wikipedia(self, term):
        try:
            headers = {
                'User-Agent': 'WikiLookupTool/1.0 (mailto:your.email@example.com) Python/3.8'
            }
            response = requests.get(
                "https://en.wikipedia.org/w/api.php",
                headers=headers,
                params={
                    "action": "query",
                    "format": "json",
                    "prop": "extracts|info|pageimages",
                    "titles": term,
                    "redirects": 1,
                    "inprop": "url",
                    "exintro": 1,
                    "pithumbsize": 400  # Request slightly larger thumbnail
                },
                timeout=5
            )
            response.raise_for_status()
            data = response.json()
            
            pages = data['query']['pages']
            page = next(iter(pages.values()))
            
            if 'missing' in page:
                return {
                    'title': term,
                    'extract': 'No Wikipedia entry found.',
                    'thumbnail': None
                }
            
            thumbnail_url = None
            if 'thumbnail' in page:
                thumbnail_url = page['thumbnail']['source']
            
            return {
                'title': page.get('title', term),
                'extract': page.get('extract', 'No content available.'),
                'thumbnail': thumbnail_url
            }
            
        except requests.RequestException as e:
            return {'title': term, 'extract': f"Error fetching content: {str(e)}", 'thumbnail': None}
        except Exception as e:
            return {'title': term, 'extract': f"Unexpected error: {str(e)}", 'thumbnail': None}

    def load_content(self):
        self.show_loading()
        
        # Load image if available
        if self.wiki_data['thumbnail']:
            self.image_label.setImage(self.wiki_data['thumbnail'])
            self.image_label.show()
        else:
            self.image_label.hide()
        
        # Set HTML content with styling
        html_content = f"""
            <html>
            <head>
                <style>
                    body {{ 
                        font-family: system-ui, -apple-system, sans-serif;
                        font-size: 14px;  /* Increased base font size */
                        line-height: 1.5;
                        margin: 8px;
                        -webkit-user-select: text;
                        user-select: text;
                        cursor: text;
                    }}
                    h2 {{
                        font-size: 18px;  /* Larger title */
                        margin: 0 0 12px 0;
                        color: #333;
                    }}
                    p {{ 
                        margin: 0 0 12px 0;
                        font-size: 14px;  /* Explicit paragraph font size */
                    }}
                    ::selection {{ background: #b4d5fe; }}
                </style>
            </head>
            <body>
                <h2>{self.wiki_data['title']}</h2>
                {self.wiki_data['extract']}
            </body>
            </html>
        """
        self.text_view.setHtml(html_content)
        
        self.hide_loading()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        super().keyPressEvent(event)

def get_selection():
    try:
        # En Windows, usamos el portapapeles primario
        clipboard = QApplication.clipboard()
        selection = clipboard.text(QClipboard.Mode.Clipboard)
        return selection.strip() if selection else None
    except:
        return None

def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    clipboard = QApplication.clipboard()
    
    win = None
    last_text = None
    last_check_time = 0
    
    def check_selection():
        nonlocal win, last_text, last_check_time
        
        current_time = time.time()
        if current_time - last_check_time < 0.1:  # 100ms minimum between checks
            return
        last_check_time = current_time
        
        # Intentar obtener la selección actual usando el portapapeles
        current_clipboard = clipboard.text()
        text = current_clipboard.strip() if current_clipboard else None
        
        if text and text != last_text:
            try:
                if win and not win.is_destroyed():
                    win.close()
            except (RuntimeError, ReferenceError):
                pass
            
            win = LookupWindow(text)
            win.show()
            last_text = text
        elif not text:
            last_text = None
            try:
                if win and not win.is_destroyed():
                    win.close()
            except (RuntimeError, ReferenceError):
                pass
            win = None
    
    # Usar un QTimer para verificar la selección periódicamente
    check_timer = QTimer()
    check_timer.timeout.connect(check_selection)
    check_timer.start(100)  # Verificar cada 100ms
    
    # Conectar también al cambio de portapapeles para mayor responsividad
    clipboard.dataChanged.connect(check_selection)
    
    # Create main window
    main_window = QMainWindow()
    
    # Create a toolbar and add the lookup action
    toolbar = QToolBar()
    main_window.addToolBar(toolbar)
    lookup_action = QAction("Look up Wikipedia", main_window)
    lookup_action.triggered.connect(lambda: check_selection())  # Invoke the same check_selection function
    toolbar.addAction(lookup_action)
    
    # Create the main content area
    central_widget = QWidget()
    central_layout = QVBoxLayout(central_widget)
    text_edit = RichTextEdit()
    central_layout.addWidget(text_edit)
    main_window.setCentralWidget(central_widget)
    
    main_window.setWindowTitle("Wikipedia Lookup Tool")
    main_window.show()

    return app.exec()

if __name__ == '__main__':
    sys.exit(main())
