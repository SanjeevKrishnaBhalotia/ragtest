"""
UI Dialogs for LocalRAG Application
Login, Database Creation, Document Import, and Model Download dialogs
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import requests
from datetime import datetime

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGridLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit, QComboBox, QCheckBox,
    QListWidget, QListWidgetItem, QProgressBar, QFileDialog, QMessageBox,
    QDialogButtonBox, QGroupBox, QSpinBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QFrame, QScrollArea
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QPixmap, QPalette, QColor

from utils.logger import get_logger

logger = get_logger(__name__)

class LoginDialog(QDialog):
    """Login dialog to collect master password"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("LocalRAG - Secure Login")
        self.setModal(True)
        self.setFixedSize(400, 300)

        self.password = None
        self.init_ui()

    def init_ui(self):
        """Initialize the login UI"""
        layout = QVBoxLayout(self)

        # Header
        header_label = QLabel("LocalRAG - Secure AI Assistant")
        header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_font = QFont()
        header_font.setPointSize(16)
        header_font.setBold(True)
        header_label.setFont(header_font)
        layout.addWidget(header_label)

        # Description
        desc_label = QLabel(
            "Enter your master password to access your encrypted knowledge bases.\n\n"
            "This password encrypts all your data using AES-256 encryption.\n"
            "If you forget this password, your data cannot be recovered."
        )
        desc_label.setWordWrap(True)
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(desc_label)

        layout.addStretch()

        # Password input
        password_frame = QFrame()
        password_layout = QFormLayout(password_frame)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("Enter master password...")
        self.password_input.returnPressed.connect(self.accept)

        password_layout.addRow("Master Password:", self.password_input)
        layout.addWidget(password_frame)

        # Show password checkbox
        self.show_password_check = QCheckBox("Show password")
        self.show_password_check.toggled.connect(self.toggle_password_visibility)
        layout.addWidget(self.show_password_check)

        layout.addStretch()

        # Buttons
        button_layout = QHBoxLayout()

        self.login_btn = QPushButton("Login")
        self.login_btn.clicked.connect(self.accept)
        self.login_btn.setDefault(True)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)

        button_layout.addWidget(self.cancel_btn)
        button_layout.addWidget(self.login_btn)

        layout.addLayout(button_layout)

        # Focus on password input
        self.password_input.setFocus()

    def toggle_password_visibility(self, checked: bool):
        """Toggle password visibility"""
        if checked:
            self.password_input.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            self.password_input.setEchoMode(QLineEdit.EchoMode.Password)

    def accept(self):
        """Accept the dialog and validate password"""
        password = self.password_input.text().strip()

        if not password:
            QMessageBox.warning(self, "Invalid Password", "Please enter a password.")
            return

        if len(password) < 8:
            QMessageBox.warning(self, "Weak Password", "Password must be at least 8 characters long.")
            return

        self.password = password
        super().accept()

    def get_password(self) -> str:
        """Get the entered password"""
        return self.password

class DatabaseCreateDialog(QDialog):
    """Dialog for creating new databases"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create New Database")
        self.setModal(True)
        self.setFixedSize(500, 300)

        self.init_ui()

    def init_ui(self):
        """Initialize the create database UI"""
        layout = QVBoxLayout(self)

        # Header
        header_label = QLabel("Create New Knowledge Base")
        header_font = QFont()
        header_font.setPointSize(14)
        header_font.setBold(True)
        header_label.setFont(header_font)
        layout.addWidget(header_label)

        # Form
        form_frame = QFrame()
        form_layout = QFormLayout(form_frame)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g., Client Project Alpha")

        self.description_input = QTextEdit()
        self.description_input.setMaximumHeight(100)
        self.description_input.setPlaceholderText("Optional description of this knowledge base...")

        form_layout.addRow("Database Name:", self.name_input)
        form_layout.addRow("Description:", self.description_input)

        layout.addWidget(form_frame)

        # Info text
        info_label = QLabel(
            "The database will be encrypted with AES-256 using your master password.\n"
            "You can add documents to this database after creation."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #666666; font-style: italic;")
        layout.addWidget(info_label)

        layout.addStretch()

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        layout.addWidget(button_box)

        # Focus on name input
        self.name_input.setFocus()

    def accept(self):
        """Validate and accept the dialog"""
        name = self.name_input.text().strip()

        if not name:
            QMessageBox.warning(self, "Invalid Name", "Please enter a database name.")
            return

        if len(name) < 3:
            QMessageBox.warning(self, "Invalid Name", "Database name must be at least 3 characters long.")
            return

        # Check for invalid characters
        invalid_chars = '<>:"/\\|?*'
        if any(char in name for char in invalid_chars):
            QMessageBox.warning(self, "Invalid Name", f"Database name cannot contain: {invalid_chars}")
            return

        super().accept()

    def get_database_info(self) -> Tuple[str, str]:
        """Get the database name and description"""
        return self.name_input.text().strip(), self.description_input.toPlainText().strip()

class DocumentImportDialog(QDialog):
    """Dialog for importing documents into a database"""

    def __init__(self, parent=None, database_name: str = "", document_processor=None):
        super().__init__(parent)
        self.setWindowTitle(f"Import Documents - {database_name}")
        self.setModal(True)
        self.setFixedSize(700, 500)

        self.database_name = database_name
        self.document_processor = document_processor
        self.selected_files = []

        self.init_ui()

    def init_ui(self):
        """Initialize the document import UI"""
        layout = QVBoxLayout(self)

        # Header
        header_label = QLabel(f"Import Documents to '{self.database_name}'")
        header_font = QFont()
        header_font.setPointSize(14)
        header_font.setBold(True)
        header_label.setFont(header_font)
        layout.addWidget(header_label)

        # File selection
        file_group = QGroupBox("Select Files")
        file_layout = QVBoxLayout(file_group)

        file_buttons = QHBoxLayout()

        self.select_files_btn = QPushButton("Select Files")
        self.select_files_btn.clicked.connect(self.select_files)

        self.select_folder_btn = QPushButton("Select Folder")
        self.select_folder_btn.clicked.connect(self.select_folder)

        self.clear_files_btn = QPushButton("Clear")
        self.clear_files_btn.clicked.connect(self.clear_files)

        file_buttons.addWidget(self.select_files_btn)
        file_buttons.addWidget(self.select_folder_btn)
        file_buttons.addWidget(self.clear_files_btn)
        file_buttons.addStretch()

        file_layout.addLayout(file_buttons)

        # Files list
        self.files_list = QListWidget()
        file_layout.addWidget(self.files_list)

        layout.addWidget(file_group)

        # Processing options
        options_group = QGroupBox("Processing Options")
        options_layout = QFormLayout(options_group)

        self.chunking_combo = QComboBox()
        self.chunking_combo.addItems(["General", "Statute (Legal)", "Letter/Report"])

        self.chunk_size_spin = QSpinBox()
        self.chunk_size_spin.setRange(100, 2000)
        self.chunk_size_spin.setValue(1000)

        self.chunk_overlap_spin = QSpinBox()
        self.chunk_overlap_spin.setRange(0, 500)
        self.chunk_overlap_spin.setValue(200)

        options_layout.addRow("Chunking Mode:", self.chunking_combo)
        options_layout.addRow("Chunk Size:", self.chunk_size_spin)
        options_layout.addRow("Chunk Overlap:", self.chunk_overlap_spin)

        layout.addWidget(options_group)

        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.import_documents)
        button_box.rejected.connect(self.reject)

        layout.addWidget(button_box)

    def select_files(self):
        """Select individual files"""
        if not self.document_processor:
            return

        extensions = self.document_processor.get_supported_extensions()
        filter_str = "Supported Files (" + " ".join(f"*{ext}" for ext in extensions) + ")"

        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Documents",
            "",
            filter_str
        )

        if files:
            self.add_files(files)

    def select_folder(self):
        """Select all supported files from a folder"""
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")

        if folder and self.document_processor:
            extensions = self.document_processor.get_supported_extensions()
            files = []

            for ext in extensions:
                files.extend(Path(folder).glob(f"**/*{ext}"))

            if files:
                self.add_files([str(f) for f in files])
            else:
                QMessageBox.information(self, "No Files", "No supported files found in the selected folder.")

    def add_files(self, file_paths: List[str]):
        """Add files to the list"""
        for file_path in file_paths:
            if file_path not in self.selected_files:
                self.selected_files.append(file_path)

                # Validate file
                validation = self.document_processor.validate_file(Path(file_path))

                file_name = Path(file_path).name
                if validation['valid']:
                    status = f"✓ {validation['size_mb']} MB"
                else:
                    status = f"✗ {validation['error']}"

                item_text = f"{file_name} - {status}"
                item = QListWidgetItem(item_text)
                item.setData(Qt.ItemDataRole.UserRole, {'path': file_path, 'valid': validation['valid']})

                self.files_list.addItem(item)

    def clear_files(self):
        """Clear all selected files"""
        self.selected_files.clear()
        self.files_list.clear()

    def import_documents(self):
        """Import the selected documents"""
        if not self.selected_files:
            QMessageBox.warning(self, "No Files", "Please select files to import.")
            return

        # Check for valid files
        valid_files = []
        for i in range(self.files_list.count()):
            item = self.files_list.item(i)
            data = item.data(Qt.ItemDataRole.UserRole)
            if data['valid']:
                valid_files.append(data['path'])

        if not valid_files:
            QMessageBox.warning(self, "No Valid Files", "No valid files selected for import.")
            return

        # Show progress
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, len(valid_files))
        self.progress_bar.setValue(0)

        # Process files
        chunking_mode = self.chunking_combo.currentText().lower().split()[0]
        all_documents = []

        try:
            for i, file_path in enumerate(valid_files):
                self.progress_bar.setValue(i)

                documents = self.document_processor.process_file(
                    Path(file_path),
                    chunking_mode,
                    {'imported_at': datetime.now().isoformat()}
                )

                if documents:
                    all_documents.extend(documents)

            self.progress_bar.setValue(len(valid_files))

            if all_documents:
                # Here you would add documents to the database
                # This would be handled by the parent window
                QMessageBox.information(
                    self, 
                    "Import Complete", 
                    f"Successfully processed {len(all_documents)} document chunks from {len(valid_files)} files."
                )
                self.accept()
            else:
                QMessageBox.warning(self, "Import Failed", "No documents were successfully processed.")

        except Exception as e:
            QMessageBox.critical(self, "Import Error", f"Failed to import documents: {e}")

        finally:
            self.progress_bar.setVisible(False)

class ModelDownloadDialog(QDialog):
    """Dialog for downloading AI models"""

    def __init__(self, parent=None, available_models: List[Dict[str, Any]] = None):
        super().__init__(parent)
        self.setWindowTitle("Download AI Models")
        self.setModal(True)
        self.setFixedSize(600, 400)

        self.available_models = available_models or []
        self.download_worker = None

        self.init_ui()

    def init_ui(self):
        """Initialize the model download UI"""
        layout = QVBoxLayout(self)

        # Header
        header_label = QLabel("Download AI Models")
        header_font = QFont()
        header_font.setPointSize(14)
        header_font.setBold(True)
        header_label.setFont(header_font)
        layout.addWidget(header_label)

        # Models table
        models_group = QGroupBox("Available Models")
        models_layout = QVBoxLayout(models_group)

        self.models_table = QTableWidget()
        self.models_table.setColumnCount(4)
        self.models_table.setHorizontalHeaderLabels(["Model", "Size", "RAM Required", "Action"])

        # Populate table
        self.models_table.setRowCount(len(self.available_models))

        for i, model in enumerate(self.available_models):
            # Model name
            name_item = QTableWidgetItem(model['name'])
            self.models_table.setItem(i, 0, name_item)

            # Size
            size_item = QTableWidgetItem(f"{model['size_gb']} GB")
            self.models_table.setItem(i, 1, size_item)

            # RAM required
            ram_item = QTableWidgetItem(f"{model['ram_required_gb']} GB")
            self.models_table.setItem(i, 2, ram_item)

            # Download button
            download_btn = QPushButton("Download")
            download_btn.clicked.connect(lambda checked, idx=i: self.download_model(idx))
            self.models_table.setCellWidget(i, 3, download_btn)

        # Resize columns
        header = self.models_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)

        models_layout.addWidget(self.models_table)
        layout.addWidget(models_group)

        # Progress
        self.progress_group = QGroupBox("Download Progress")
        self.progress_group.setVisible(False)
        progress_layout = QVBoxLayout(self.progress_group)

        self.download_progress = QProgressBar()
        self.download_status = QLabel("Ready to download...")

        progress_layout.addWidget(self.download_status)
        progress_layout.addWidget(self.download_progress)

        layout.addWidget(self.progress_group)

        # Info
        info_label = QLabel(
            "Models will be downloaded to the models folder.\n"
            "Large models may take several minutes to download depending on your internet connection."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #666666; font-style: italic;")
        layout.addWidget(info_label)

        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(self.reject)

        layout.addWidget(button_box)

    def download_model(self, model_index: int):
        """Download a specific model"""
        if self.download_worker and self.download_worker.isRunning():
            QMessageBox.warning(self, "Download In Progress", "Please wait for the current download to complete.")
            return

        model = self.available_models[model_index]

        # Confirm download
        reply = QMessageBox.question(
            self,
            "Confirm Download",
            f"Download {model['name']}?\n\nSize: {model['size_gb']} GB\n"
            f"This may take several minutes depending on your internet connection.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        # Disable download button
        download_btn = self.models_table.cellWidget(model_index, 3)
        download_btn.setEnabled(False)
        download_btn.setText("Downloading...")

        # Show progress
        self.progress_group.setVisible(True)
        self.download_progress.setRange(0, 0)  # Indeterminate
        self.download_status.setText(f"Downloading {model['name']}...")

        # Start download worker
        self.download_worker = ModelDownloadWorker(model)
        self.download_worker.progress_update.connect(self.update_download_progress)
        self.download_worker.download_complete.connect(lambda: self.download_completed(model_index, True))
        self.download_worker.download_error.connect(lambda error: self.download_completed(model_index, False, error))
        self.download_worker.start()

    def update_download_progress(self, message: str):
        """Update download progress"""
        self.download_status.setText(message)

    def download_completed(self, model_index: int, success: bool, error: str = ""):
        """Handle download completion"""
        download_btn = self.models_table.cellWidget(model_index, 3)

        if success:
            download_btn.setText("✓ Downloaded")
            download_btn.setEnabled(False)
            self.download_status.setText("Download completed successfully!")

            QMessageBox.information(self, "Download Complete", "Model downloaded successfully!")
        else:
            download_btn.setText("Download")
            download_btn.setEnabled(True)
            self.download_status.setText(f"Download failed: {error}")

            QMessageBox.critical(self, "Download Failed", f"Failed to download model:\n{error}")

        self.progress_group.setVisible(False)

class ModelDownloadWorker(QThread):
    """Worker thread for downloading models"""

    progress_update = pyqtSignal(str)
    download_complete = pyqtSignal()
    download_error = pyqtSignal(str)

    def __init__(self, model_info: Dict[str, Any]):
        super().__init__()
        self.model_info = model_info

    def run(self):
        """Download the model file"""
        try:
            models_dir = Path(__file__).parent.parent.parent.parent / "models"
            models_dir.mkdir(exist_ok=True)

            file_path = models_dir / Path(self.model_info['file_path']).name
            url = self.model_info['download_url']

            self.progress_update.emit(f"Starting download of {self.model_info['name']}...")

            # Download with progress
            response = requests.get(url, stream=True)
            response.raise_for_status()

            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0

            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)

                        if total_size > 0:
                            progress = (downloaded / total_size) * 100
                            self.progress_update.emit(f"Downloaded {progress:.1f}% ({downloaded // 1024 // 1024} MB)")

            self.progress_update.emit("Download completed!")
            self.download_complete.emit()

        except Exception as e:
            self.download_error.emit(str(e))
