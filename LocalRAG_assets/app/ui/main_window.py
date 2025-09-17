"""
Main Window - PyQt6 GUI with complete tabbed interface
Implements the complete user interface for LocalRAG
"""

import sys
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
import json
import webbrowser
from datetime import datetime

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QTextEdit, QLineEdit, QPushButton, QLabel, QListWidget, QListWidgetItem,
    QComboBox, QCheckBox, QProgressBar, QSplitter, QGroupBox, QFormLayout,
    QFileDialog, QMessageBox, QDialog, QDialogButtonBox, QTextBrowser,
    QScrollArea, QFrame, QGridLayout, QSlider, QSpinBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, pyqtSlot
from PyQt6.QtGui import QFont, QTextCursor, QPixmap, QPalette, QColor

from components.rag_pipeline import RAGPipeline
from components.document_processor import DocumentProcessor
from components.prompt_workshop import PromptWorkshop
from utils.logger import get_logger
from ui.dialogs import LoginDialog, ModelDownloadDialog, DatabaseCreateDialog, DocumentImportDialog

logger = get_logger(__name__)

class QueryWorker(QThread):
    """Worker thread for running RAG queries"""

    progress_update = pyqtSignal(str)
    query_complete = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)

    def __init__(self, rag_pipeline: RAGPipeline, query: str, database_names: List[str]):
        super().__init__()
        self.rag_pipeline = rag_pipeline
        self.query = query
        self.database_names = database_names

    def run(self):
        """Run the query in background thread"""
        try:
            if len(self.database_names) == 1:
                result = self.rag_pipeline.query_single_database(
                    self.query, 
                    self.database_names[0], 
                    progress_callback=self.progress_update.emit
                )
            else:
                result = self.rag_pipeline.query_multiple_databases(
                    self.query, 
                    self.database_names, 
                    progress_callback=self.progress_update.emit
                )

            self.query_complete.emit(result)

        except Exception as e:
            self.error_occurred.emit(str(e))

class ChainWorker(QThread):
    """Worker thread for running prompt chains"""

    progress_update = pyqtSignal(str)
    step_complete = pyqtSignal(int, dict)
    chain_complete = pyqtSignal(list)
    error_occurred = pyqtSignal(str)

    def __init__(self, prompt_workshop, chain_id: str, initial_variables: Dict[str, Any], rag_pipeline):
        super().__init__()
        self.prompt_workshop = prompt_workshop
        self.chain_id = chain_id
        self.initial_variables = initial_variables
        self.rag_pipeline = rag_pipeline

    def run(self):
        """Run the chain execution in background thread"""
        try:
            results = self.prompt_workshop.execute_chain(
                self.chain_id,
                self.initial_variables,
                self.rag_pipeline,
                progress_callback=self.progress_update.emit
            )

            # Emit step completion signals
            for result in results:
                self.step_complete.emit(result['step_number'], result)

            self.chain_complete.emit(results)

        except Exception as e:
            self.error_occurred.emit(str(e))

class MainWindow(QMainWindow):
    """Main application window with complete tabbed interface"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("LocalRAG - Secure Local AI Assistant")
        self.setGeometry(100, 100, 1400, 900)

        # Initialize components
        self.config_path = Path(__file__).parent.parent / "config" / "config.json"
        self.models_dir = Path(__file__).parent.parent.parent / "models"
        self.databases_dir = Path(__file__).parent.parent.parent / "databases"
        self.prompts_dir = Path(__file__).parent.parent.parent / "prompts"

        self.rag_pipeline = None
        self.document_processor = None
        self.prompt_workshop = None
        self.current_query_worker = None
        self.current_chain_worker = None

        # Load configuration
        self.load_configuration()

        # Initialize UI
        self.init_ui()

        # Show login dialog
        self.show_login_dialog()

        logger.info("MainWindow initialized")

    def load_configuration(self):
        """Load application configuration"""
        try:
            with open(self.config_path, 'r') as f:
                self.config = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            self.config = {}

    def init_ui(self):
        """Initialize the user interface"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        main_layout = QVBoxLayout(central_widget)

        # Create tab widget
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)

        # Create tabs
        self.create_query_tab()
        self.create_databases_tab()
        self.create_models_tab()
        self.create_prompt_workshop_tab()
        self.create_settings_tab()

        # Status bar
        self.statusBar().showMessage("Ready - Please login to continue")

        # Apply styling
        self.apply_styling()

    def create_query_tab(self):
        """Create the main query interface tab"""
        query_widget = QWidget()
        layout = QHBoxLayout(query_widget)

        # Left panel - Query interface
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        # Model selection
        model_group = QGroupBox("AI Model")
        model_layout = QFormLayout(model_group)

        self.model_combo = QComboBox()
        self.model_combo.currentTextChanged.connect(self.on_model_changed)
        model_layout.addRow("Current Model:", self.model_combo)

        self.model_info_label = QLabel("No model loaded")
        self.model_info_label.setWordWrap(True)
        model_layout.addRow("Info:", self.model_info_label)

        left_layout.addWidget(model_group)

        # Database selection
        db_group = QGroupBox("Knowledge Bases")
        db_layout = QVBoxLayout(db_group)

        self.database_list = QListWidget()
        self.database_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        db_layout.addWidget(self.database_list)

        db_buttons = QHBoxLayout()
        self.refresh_db_btn = QPushButton("Refresh")
        self.refresh_db_btn.clicked.connect(self.refresh_databases)
        db_buttons.addWidget(self.refresh_db_btn)

        db_buttons.addStretch()
        db_layout.addLayout(db_buttons)

        left_layout.addWidget(db_group)

        # Query input
        query_group = QGroupBox("Ask a Question")
        query_layout = QVBoxLayout(query_group)

        self.query_input = QTextEdit()
        self.query_input.setMaximumHeight(100)
        self.query_input.setPlaceholderText("Type your question here...")
        query_layout.addWidget(self.query_input)

        query_buttons = QHBoxLayout()
        self.ask_button = QPushButton("Ask Question")
        self.ask_button.clicked.connect(self.ask_question)
        self.ask_button.setEnabled(False)

        self.clear_button = QPushButton("Clear")
        self.clear_button.clicked.connect(self.clear_query)

        query_buttons.addWidget(self.ask_button)
        query_buttons.addWidget(self.clear_button)
        query_buttons.addStretch()

        query_layout.addLayout(query_buttons)
        left_layout.addWidget(query_group)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        left_layout.addWidget(self.progress_bar)

        # Real-time feedback
        self.feedback_text = QTextEdit()
        self.feedback_text.setMaximumHeight(80)
        self.feedback_text.setVisible(False)
        left_layout.addWidget(self.feedback_text)

        left_layout.addStretch()

        # Right panel - Results
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        # Answer display
        answer_group = QGroupBox("Answer")
        answer_layout = QVBoxLayout(answer_group)

        self.answer_display = QTextBrowser()
        self.answer_display.setOpenExternalLinks(True)
        answer_layout.addWidget(self.answer_display)

        # Confidence and model info
        info_layout = QHBoxLayout()
        self.confidence_label = QLabel("Confidence: --")
        self.model_used_label = QLabel("Model: --")
        info_layout.addWidget(self.confidence_label)
        info_layout.addStretch()
        info_layout.addWidget(self.model_used_label)
        answer_layout.addLayout(info_layout)

        right_layout.addWidget(answer_group)

        # Sources display
        sources_group = QGroupBox("Sources")
        sources_layout = QVBoxLayout(sources_group)

        self.sources_list = QListWidget()
        sources_layout.addWidget(self.sources_list)

        right_layout.addWidget(sources_group)

        # Create splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([400, 600])

        layout.addWidget(splitter)

        self.tab_widget.addTab(query_widget, "Query Assistant")

    def create_databases_tab(self):
        """Create the database management tab"""
        db_widget = QWidget()
        layout = QHBoxLayout(db_widget)

        # Left panel - Database list
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        # Database list
        db_list_group = QGroupBox("Available Databases")
        db_list_layout = QVBoxLayout(db_list_group)

        self.db_management_list = QListWidget()
        self.db_management_list.itemSelectionChanged.connect(self.on_database_selected)
        db_list_layout.addWidget(self.db_management_list)

        # Database management buttons
        db_mgmt_buttons = QGridLayout()

        self.create_db_btn = QPushButton("Create New")
        self.create_db_btn.clicked.connect(self.create_database)

        self.import_docs_btn = QPushButton("Import Documents")
        self.import_docs_btn.clicked.connect(self.import_documents)
        self.import_docs_btn.setEnabled(False)

        self.delete_db_btn = QPushButton("Delete Database")
        self.delete_db_btn.clicked.connect(self.delete_database)
        self.delete_db_btn.setEnabled(False)

        self.export_db_btn = QPushButton("Export Database")
        self.export_db_btn.clicked.connect(self.export_database)
        self.export_db_btn.setEnabled(False)

        db_mgmt_buttons.addWidget(self.create_db_btn, 0, 0)
        db_mgmt_buttons.addWidget(self.import_docs_btn, 0, 1)
        db_mgmt_buttons.addWidget(self.delete_db_btn, 1, 0)
        db_mgmt_buttons.addWidget(self.export_db_btn, 1, 1)

        db_list_layout.addLayout(db_mgmt_buttons)
        left_layout.addWidget(db_list_group)

        left_layout.addStretch()

        # Right panel - Database details
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        # Database info
        self.db_info_group = QGroupBox("Database Information")
        self.db_info_layout = QFormLayout(self.db_info_group)

        self.db_name_label = QLabel("--")
        self.db_description_label = QLabel("--")
        self.db_doc_count_label = QLabel("--")
        self.db_created_label = QLabel("--")
        self.db_size_label = QLabel("--")

        self.db_info_layout.addRow("Name:", self.db_name_label)
        self.db_info_layout.addRow("Description:", self.db_description_label)
        self.db_info_layout.addRow("Documents:", self.db_doc_count_label)
        self.db_info_layout.addRow("Created:", self.db_created_label)
        self.db_info_layout.addRow("Size:", self.db_size_label)

        right_layout.addWidget(self.db_info_group)

        # Document list
        docs_group = QGroupBox("Documents")
        docs_layout = QVBoxLayout(docs_group)

        self.documents_list = QListWidget()
        docs_layout.addWidget(self.documents_list)

        right_layout.addWidget(docs_group)

        # Create splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([400, 600])

        layout.addWidget(splitter)

        self.tab_widget.addTab(db_widget, "Databases")

    def create_models_tab(self):
        """Create the models management tab"""
        models_widget = QWidget()
        layout = QVBoxLayout(models_widget)

        # Models list
        models_group = QGroupBox("Available Models")
        models_layout = QVBoxLayout(models_group)

        self.models_list = QListWidget()
        models_layout.addWidget(self.models_list)

        # Model management buttons
        model_buttons = QHBoxLayout()

        self.download_model_btn = QPushButton("Download Model")
        self.download_model_btn.clicked.connect(self.download_model)

        self.refresh_models_btn = QPushButton("Refresh")
        self.refresh_models_btn.clicked.connect(self.refresh_models)

        self.delete_model_btn = QPushButton("Delete Model")
        self.delete_model_btn.clicked.connect(self.delete_model)

        model_buttons.addWidget(self.download_model_btn)
        model_buttons.addWidget(self.refresh_models_btn)
        model_buttons.addWidget(self.delete_model_btn)
        model_buttons.addStretch()

        models_layout.addLayout(model_buttons)
        layout.addWidget(models_group)

        # Model info
        info_group = QGroupBox("Model Information")
        info_layout = QFormLayout(info_group)

        self.model_name_label = QLabel("Select a model to view details")
        self.model_size_label = QLabel("--")
        self.model_ram_label = QLabel("--")
        self.model_context_label = QLabel("--")
        self.model_status_label = QLabel("--")

        info_layout.addRow("Name:", self.model_name_label)
        info_layout.addRow("Size:", self.model_size_label)
        info_layout.addRow("RAM Required:", self.model_ram_label)
        info_layout.addRow("Context Length:", self.model_context_label)
        info_layout.addRow("Status:", self.model_status_label)

        layout.addWidget(info_group)

        layout.addStretch()

        self.tab_widget.addTab(models_widget, "AI Models")

    def create_prompt_workshop_tab(self):
        """Create the Prompt Workshop tab for advanced templating and chaining"""
        workshop_widget = QWidget()
        layout = QHBoxLayout(workshop_widget)

        # Left panel - Templates and Chains
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        # Template selection
        template_group = QGroupBox("Prompt Templates")
        template_layout = QVBoxLayout(template_group)

        self.template_list = QListWidget()
        self.template_list.itemSelectionChanged.connect(self.on_template_selected)
        template_layout.addWidget(self.template_list)

        template_buttons = QHBoxLayout()
        self.use_template_btn = QPushButton("Use Template")
        self.use_template_btn.clicked.connect(self.use_selected_template)
        self.use_template_btn.setEnabled(False)

        template_buttons.addWidget(self.use_template_btn)
        template_buttons.addStretch()
        template_layout.addLayout(template_buttons)

        left_layout.addWidget(template_group)

        # Chain selection
        chain_group = QGroupBox("Prompt Chains")
        chain_layout = QVBoxLayout(chain_group)

        self.chain_list = QListWidget()
        self.chain_list.itemSelectionChanged.connect(self.on_chain_selected)
        chain_layout.addWidget(self.chain_list)

        chain_buttons = QHBoxLayout()
        self.run_chain_btn = QPushButton("Run Chain")
        self.run_chain_btn.clicked.connect(self.run_selected_chain)
        self.run_chain_btn.setEnabled(False)

        chain_buttons.addWidget(self.run_chain_btn)
        chain_buttons.addStretch()
        chain_layout.addLayout(chain_buttons)

        left_layout.addWidget(chain_group)

        # Right panel - Preview and Results
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        # Template preview
        preview_group = QGroupBox("Template Preview")
        preview_layout = QVBoxLayout(preview_group)

        self.template_preview = QTextBrowser()
        self.template_preview.setMaximumHeight(200)
        preview_layout.addWidget(self.template_preview)

        right_layout.addWidget(preview_group)

        # Variables input
        variables_group = QGroupBox("Template Variables")
        variables_layout = QFormLayout(variables_group)

        self.query_variable = QLineEdit()
        self.query_variable.setPlaceholderText("Enter your query here...")
        variables_layout.addRow("Query:", self.query_variable)

        right_layout.addWidget(variables_group)

        # Chain progress
        self.chain_progress_group = QGroupBox("Chain Execution Progress")
        self.chain_progress_group.setVisible(False)
        chain_progress_layout = QVBoxLayout(self.chain_progress_group)

        self.chain_progress_text = QTextEdit()
        self.chain_progress_text.setMaximumHeight(100)
        chain_progress_layout.addWidget(self.chain_progress_text)

        self.chain_progress_bar = QProgressBar()
        chain_progress_layout.addWidget(self.chain_progress_bar)

        right_layout.addWidget(self.chain_progress_group)

        # Results display
        results_group = QGroupBox("Results")
        results_layout = QVBoxLayout(results_group)

        self.chain_results = QTextBrowser()
        self.chain_results.setOpenExternalLinks(True)
        results_layout.addWidget(self.chain_results)

        right_layout.addWidget(results_group)

        # Create splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([400, 600])

        layout.addWidget(splitter)

        self.tab_widget.addTab(workshop_widget, "Prompt Workshop")

    def create_settings_tab(self):
        """Create the settings tab"""
        settings_widget = QWidget()
        layout = QVBoxLayout(settings_widget)

        # General settings
        general_group = QGroupBox("General Settings") 
        general_layout = QFormLayout(general_group)

        self.chunk_size_spin = QSpinBox()
        self.chunk_size_spin.setRange(100, 2000)
        self.chunk_size_spin.setValue(1000)

        self.chunk_overlap_spin = QSpinBox()
        self.chunk_overlap_spin.setRange(0, 500)
        self.chunk_overlap_spin.setValue(200)

        self.max_chunks_spin = QSpinBox()
        self.max_chunks_spin.setRange(1, 20)
        self.max_chunks_spin.setValue(5)

        general_layout.addRow("Chunk Size:", self.chunk_size_spin)
        general_layout.addRow("Chunk Overlap:", self.chunk_overlap_spin)
        general_layout.addRow("Max Chunks per Query:", self.max_chunks_spin)

        layout.addWidget(general_group)

        # Security settings
        security_group = QGroupBox("Security Settings")
        security_layout = QFormLayout(security_group)

        self.auto_lock_check = QCheckBox("Auto-lock after inactivity")
        self.audit_log_check = QCheckBox("Enable audit logging")

        self.auto_lock_minutes = QSpinBox()
        self.auto_lock_minutes.setRange(5, 120)
        self.auto_lock_minutes.setValue(30)

        security_layout.addRow(self.auto_lock_check)
        security_layout.addRow("Auto-lock minutes:", self.auto_lock_minutes)
        security_layout.addRow(self.audit_log_check)

        layout.addWidget(security_group)

        # Buttons
        settings_buttons = QHBoxLayout()

        self.save_settings_btn = QPushButton("Save Settings")
        self.save_settings_btn.clicked.connect(self.save_settings)

        self.reset_settings_btn = QPushButton("Reset to Defaults")
        self.reset_settings_btn.clicked.connect(self.reset_settings)

        settings_buttons.addWidget(self.save_settings_btn)
        settings_buttons.addWidget(self.reset_settings_btn)
        settings_buttons.addStretch()

        layout.addLayout(settings_buttons)
        layout.addStretch()

        self.tab_widget.addTab(settings_widget, "Settings")

    def apply_styling(self):
        """Apply custom styling to the interface"""
        style = """
        QMainWindow {
            background-color: #f5f5f5;
        }

        QGroupBox {
            font-weight: bold;
            border: 2px solid #cccccc;
            border-radius: 5px;
            margin-top: 1ex;
            padding-top: 10px;
        }

        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 10px 0 10px;
        }

        QPushButton {
            background-color: #0078d4;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            font-weight: bold;
        }

        QPushButton:hover {
            background-color: #106ebe;
        }

        QPushButton:pressed {
            background-color: #005a9e;
        }

        QPushButton:disabled {
            background-color: #cccccc;
            color: #666666;
        }

        QTextEdit, QTextBrowser {
            border: 1px solid #cccccc;
            border-radius: 4px;
            padding: 8px;
            background-color: white;
        }

        QListWidget {
            border: 1px solid #cccccc;
            border-radius: 4px;
            background-color: white;
            alternate-background-color: #f9f9f9;
        }

        QComboBox {
            border: 1px solid #cccccc;
            border-radius: 4px;
            padding: 4px 8px;
            background-color: white;
        }
        """

        self.setStyleSheet(style)

    def show_login_dialog(self):
        """Show login dialog to get master password"""
        dialog = LoginDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            password = dialog.get_password()
            self.initialize_rag_system(password)
        else:
            self.close()

    def initialize_rag_system(self, master_password: str):
        """Initialize the RAG system with master password"""
        try:
            # Initialize RAG pipeline
            self.rag_pipeline = RAGPipeline(
                self.config_path,
                self.databases_dir,
                self.models_dir
            )
            self.rag_pipeline.set_master_password(master_password)

            # Initialize document processor
            chunk_size = self.config.get('database_settings', {}).get('chunk_size', 1000)
            chunk_overlap = self.config.get('database_settings', {}).get('chunk_overlap', 200)
            self.document_processor = DocumentProcessor(chunk_size, chunk_overlap)

            # Initialize prompt workshop
            self.prompt_workshop = PromptWorkshop(self.prompts_dir)

            # Populate UI
            self.refresh_models()
            self.refresh_databases()
            self.refresh_prompt_templates()

            # Enable UI
            self.ask_button.setEnabled(True)

            self.statusBar().showMessage("System initialized successfully")
            logger.info("RAG system initialized")

        except Exception as e:
            QMessageBox.critical(self, "Initialization Error", f"Failed to initialize system: {e}")
            self.close()

    def refresh_models(self):
        """Refresh the models list"""
        if not self.rag_pipeline:
            return

        self.model_combo.clear()
        self.models_list.clear()

        models = self.rag_pipeline.get_available_models()

        for model in models:
            # Add to combo box if available
            if model['available']:
                self.model_combo.addItem(model['name'])

            # Add to models list with status
            status = "✓ Available" if model['available'] else "✗ Not Downloaded"
            item_text = f"{model['name']} ({model['size_gb']}GB) - {status}"

            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, model)

            self.models_list.addItem(item)

        # Auto-select first available model
        if self.model_combo.count() > 0:
            self.on_model_changed(self.model_combo.currentText())

    def refresh_databases(self):
        """Refresh the databases list"""
        if not self.rag_pipeline or not self.rag_pipeline.database_manager:
            return

        self.database_list.clear()
        self.db_management_list.clear()

        databases = self.rag_pipeline.database_manager.list_databases()

        for db in databases:
            # Add to query tab database list
            item = QListWidgetItem(f"{db['name']} ({db['document_count']} docs)")
            item.setData(Qt.ItemDataRole.UserRole, db)
            self.database_list.addItem(item)

            # Add to management tab database list
            mgmt_item = QListWidgetItem(db['name'])
            mgmt_item.setData(Qt.ItemDataRole.UserRole, db)
            self.db_management_list.addItem(mgmt_item)

    def refresh_prompt_templates(self):
        """Refresh the prompt templates and chains lists"""
        if not self.prompt_workshop:
            return

        # Clear existing items
        self.template_list.clear()
        self.chain_list.clear()

        # Add templates
        templates = self.prompt_workshop.list_templates()
        for template in templates:
            item_text = f"[{template.category}] {template.name}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, template)
            self.template_list.addItem(item)

        # Add chains
        chains = self.prompt_workshop.list_chains()
        for chain in chains:
            item_text = f"{chain.name} ({len(chain.steps)} steps)"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, chain)
            self.chain_list.addItem(item)

    @pyqtSlot(str)
    def on_model_changed(self, model_name: str):
        """Handle model selection change"""
        if not self.rag_pipeline or not model_name:
            return

        # Load the selected model
        success = self.rag_pipeline.load_model(model_name)

        if success:
            # Find model info
            models = self.rag_pipeline.get_available_models()
            current_model = next((m for m in models if m['name'] == model_name), None)

            if current_model:
                info_text = f"RAM: {current_model['ram_required_gb']}GB, Context: {current_model['context_length']:,} tokens"
                self.model_info_label.setText(info_text)
                self.statusBar().showMessage(f"Model loaded: {model_name}")
        else:
            self.model_info_label.setText("Failed to load model")
            QMessageBox.warning(self, "Model Error", f"Failed to load model: {model_name}")

    def ask_question(self):
        """Handle ask question button click"""
        if not self.rag_pipeline or not self.rag_pipeline.current_model:
            QMessageBox.warning(self, "No Model", "Please select and load a model first.")
            return

        # Get query text
        query = self.query_input.toPlainText().strip()
        if not query:
            QMessageBox.warning(self, "No Query", "Please enter a question.")
            return

        # Get selected databases
        selected_databases = []
        for i in range(self.database_list.count()):
            item = self.database_list.item(i)
            if item.isSelected():
                db_data = item.data(Qt.ItemDataRole.UserRole)
                selected_databases.append(db_data['name'])

        if not selected_databases:
            QMessageBox.warning(self, "No Database", "Please select at least one database.")
            return

        # Disable UI during query
        self.ask_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.feedback_text.setVisible(True)
        self.feedback_text.clear()

        # Clear previous results
        self.answer_display.clear()
        self.sources_list.clear()
        self.confidence_label.setText("Confidence: --")
        self.model_used_label.setText("Model: --")

        # Start query worker
        self.current_query_worker = QueryWorker(self.rag_pipeline, query, selected_databases)
        self.current_query_worker.progress_update.connect(self.update_progress)
        self.current_query_worker.query_complete.connect(self.query_completed)
        self.current_query_worker.error_occurred.connect(self.query_error)
        self.current_query_worker.start()

    @pyqtSlot(str)
    def update_progress(self, message: str):
        """Update progress feedback"""
        self.feedback_text.append(message)

        # Auto-scroll to bottom
        cursor = self.feedback_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.feedback_text.setTextCursor(cursor)

    @pyqtSlot(dict)
    def query_completed(self, result: Dict[str, Any]):
        """Handle completed query"""
        # Display answer
        answer = result.get('answer', 'No answer generated.')
        self.answer_display.setHtml(f"<div style='font-size: 14px; line-height: 1.6;'>{answer}</div>")

        # Display confidence
        confidence = result.get('confidence', 0.0)
        self.confidence_label.setText(f"Confidence: {confidence:.1%}")

        # Display model used
        model_used = result.get('model_used', 'Unknown')
        self.model_used_label.setText(f"Model: {model_used}")

        # Display sources
        sources = result.get('sources', [])
        for source in sources:
            source_text = f"[{source['database']}] {source['content_preview']}"
            item = QListWidgetItem(source_text)
            item.setData(Qt.ItemDataRole.UserRole, source)
            self.sources_list.addItem(item)

        # Re-enable UI
        self.ask_button.setEnabled(True)
        self.progress_bar.setVisible(False)

        self.statusBar().showMessage(f"Query completed - {len(sources)} sources found")

    @pyqtSlot(str)
    def query_error(self, error_message: str):
        """Handle query error"""
        QMessageBox.critical(self, "Query Error", f"Query failed: {error_message}")

        # Re-enable UI
        self.ask_button.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.feedback_text.setVisible(False)

    def clear_query(self):
        """Clear query input and results"""
        self.query_input.clear()
        self.answer_display.clear()
        self.sources_list.clear()
        self.confidence_label.setText("Confidence: --")
        self.model_used_label.setText("Model: --")
        self.feedback_text.clear()
        self.feedback_text.setVisible(False)

    def create_database(self):
        """Show create database dialog"""
        dialog = DatabaseCreateDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            name, description = dialog.get_database_info()

            if self.rag_pipeline and self.rag_pipeline.database_manager:
                success = self.rag_pipeline.database_manager.create_database(name, description)
                if success:
                    self.refresh_databases()
                    QMessageBox.information(self, "Success", f"Database '{name}' created successfully.")
                else:
                    QMessageBox.warning(self, "Error", f"Failed to create database '{name}'.")

    def import_documents(self):
        """Show import documents dialog"""
        selected_items = self.db_management_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No Selection", "Please select a database first.")
            return

        db_name = selected_items[0].text()

        dialog = DocumentImportDialog(self, db_name, self.document_processor)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh_databases()
            QMessageBox.information(self, "Success", "Documents imported successfully.")

    def delete_database(self):
        """Delete selected database"""
        selected_items = self.db_management_list.selectedItems()
        if not selected_items:
            return

        db_name = selected_items[0].text()

        reply = QMessageBox.question(
            self, 
            "Confirm Delete", 
            f"Are you sure you want to delete database '{db_name}'?\n\nThis action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            if self.rag_pipeline and self.rag_pipeline.database_manager:
                success = self.rag_pipeline.database_manager.delete_database(db_name)
                if success:
                    self.refresh_databases() 
                    QMessageBox.information(self, "Success", f"Database '{db_name}' deleted.")
                else:
                    QMessageBox.warning(self, "Error", f"Failed to delete database '{db_name}'.")

    def export_database(self):
        """Export database (placeholder)"""
        QMessageBox.information(self, "Export", "Database export feature coming soon!")

    def download_model(self):
        """Show model download dialog"""
        if not self.rag_pipeline:
            return

        models = self.rag_pipeline.get_available_models()
        unavailable_models = [m for m in models if not m['available']]

        if not unavailable_models:
            QMessageBox.information(self, "All Downloaded", "All models are already downloaded.")
            return

        dialog = ModelDownloadDialog(self, unavailable_models)
        dialog.exec()

        # Refresh models after download
        self.refresh_models()

    def delete_model(self):
        """Delete selected model file"""
        selected_items = self.models_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No Selection", "Please select a model to delete.")
            return

        model_data = selected_items[0].data(Qt.ItemDataRole.UserRole)
        if not model_data['available']:
            QMessageBox.information(self, "Not Available", "Model is not downloaded.")
            return

        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Delete model '{model_data['name']}'?\n\nFile: {model_data['file_path']}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                os.remove(model_data['file_path'])
                self.refresh_models()
                QMessageBox.information(self, "Success", "Model deleted successfully.")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to delete model: {e}")

    def on_database_selected(self):
        """Handle database selection in management tab"""
        selected_items = self.db_management_list.selectedItems()

        if selected_items:
            self.import_docs_btn.setEnabled(True)
            self.delete_db_btn.setEnabled(True)
            self.export_db_btn.setEnabled(True)

            # Update database info
            db_data = selected_items[0].data(Qt.ItemDataRole.UserRole)
            if db_data:
                self.db_name_label.setText(db_data['name'])
                self.db_description_label.setText(db_data.get('description', 'No description'))
                self.db_doc_count_label.setText(str(db_data['document_count']))
                self.db_created_label.setText(db_data.get('created_at', 'Unknown'))
                self.db_size_label.setText("Calculating...")
        else:
            self.import_docs_btn.setEnabled(False)
            self.delete_db_btn.setEnabled(False)
            self.export_db_btn.setEnabled(False)

            # Clear database info
            self.db_name_label.setText("--")
            self.db_description_label.setText("--")
            self.db_doc_count_label.setText("--")
            self.db_created_label.setText("--")
            self.db_size_label.setText("--")

    def on_template_selected(self):
        """Handle template selection"""
        selected_items = self.template_list.selectedItems()

        if selected_items:
            template = selected_items[0].data(Qt.ItemDataRole.UserRole)

            # Show template preview
            preview_text = f"<h3>{template.name}</h3>"
            preview_text += f"<p><i>{template.description}</i></p>"
            preview_text += f"<p><strong>Variables:</strong> {', '.join(template.variables)}</p>"
            preview_text += f"<hr><pre>{template.template_content}</pre>"

            self.template_preview.setHtml(preview_text)
            self.use_template_btn.setEnabled(True)
        else:
            self.template_preview.clear()
            self.use_template_btn.setEnabled(False)

    def on_chain_selected(self):
        """Handle chain selection"""
        selected_items = self.chain_list.selectedItems()

        if selected_items:
            chain = selected_items[0].data(Qt.ItemDataRole.UserRole)

            # Show chain preview
            preview_text = f"<h3>{chain.name}</h3>"
            preview_text += f"<p><i>{chain.description}</i></p>"
            preview_text += f"<p><strong>Steps:</strong></p><ol>"

            for step in chain.steps:
                preview_text += f"<li>{step['name']}</li>"

            preview_text += "</ol>"

            self.template_preview.setHtml(preview_text)
            self.run_chain_btn.setEnabled(True)
        else:
            self.run_chain_btn.setEnabled(False)

    def use_selected_template(self):
        """Use the selected template for a single query"""
        QMessageBox.information(self, "Template", "Template usage feature coming soon!")

    def run_selected_chain(self):
        """Run the selected prompt chain"""
        selected_items = self.chain_list.selectedItems()
        if not selected_items:
            return

        chain = selected_items[0].data(Qt.ItemDataRole.UserRole)
        query = self.query_variable.text().strip()

        if not query:
            QMessageBox.warning(self, "No Query", "Please enter a query in the variables section.")
            return

        if not self.rag_pipeline or not self.rag_pipeline.current_model:
            QMessageBox.warning(self, "No Model", "Please select and load a model first.")
            return

        # Get selected databases
        selected_databases = []
        for i in range(self.database_list.count()):
            item = self.database_list.item(i)
            if item.isSelected():
                db_data = item.data(Qt.ItemDataRole.UserRole)
                selected_databases.append(db_data['name'])

        if not selected_databases:
            QMessageBox.warning(self, "No Database", "Please select at least one database in the Query Assistant tab.")
            return

        # Show progress
        self.chain_progress_group.setVisible(True)
        self.chain_progress_text.clear()
        self.chain_progress_bar.setRange(0, len(chain.steps))
        self.chain_progress_bar.setValue(0)
        self.chain_results.clear()

        # Get context from databases
        db_results = self.rag_pipeline.database_manager.query_databases(
            query, 
            selected_databases, 
            n_results=self.config['database_settings']['max_chunks_per_query']
        )

        # Prepare context
        context_parts = []
        for db_name, results in db_results.items():
            for result in results:
                context_parts.append(f"Source: {db_name}\n{result['content']}")

        context = "\n\n".join(context_parts)

        # Prepare initial variables
        initial_variables = {
            'query': query,
            'context': context
        }

        # Run chain in worker thread
        self.run_chain_btn.setEnabled(False)
        self.current_chain_worker = ChainWorker(self.prompt_workshop, chain.chain_id, initial_variables, self.rag_pipeline)
        self.current_chain_worker.progress_update.connect(self.update_chain_progress)
        self.current_chain_worker.step_complete.connect(self.chain_step_complete)
        self.current_chain_worker.chain_complete.connect(self.chain_execution_complete)
        self.current_chain_worker.error_occurred.connect(self.chain_error)
        self.current_chain_worker.start()

    def update_chain_progress(self, message: str):
        """Update chain execution progress"""
        self.chain_progress_text.append(message)
        cursor = self.chain_progress_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.chain_progress_text.setTextCursor(cursor)

    def chain_step_complete(self, step_number: int, step_result: Dict[str, Any]):
        """Handle completion of a chain step"""
        self.chain_progress_bar.setValue(step_number)

        # Add step result to display
        result_html = f"<h4>Step {step_number}: {step_result['step_name']}</h4>"
        result_html += f"<div style='background-color: #f5f5f5; padding: 10px; margin: 5px 0; border-radius: 5px;'>"
        result_html += f"{step_result.get('answer', 'No answer generated.')}"
        result_html += f"</div><hr>"

        current_html = self.chain_results.toHtml()
        self.chain_results.setHtml(current_html + result_html)

    def chain_execution_complete(self, results: List[Dict[str, Any]]):
        """Handle completion of entire chain"""
        self.run_chain_btn.setEnabled(True)

        # Add final summary
        final_html = "<h3>🎉 Chain Execution Complete!</h3>"
        final_html += f"<p>Successfully executed {len(results)} steps.</p>"

        if results:
            final_result = results[-1]
            final_html += "<h4>Final Result:</h4>"
            final_html += f"<div style='background-color: #e8f5e8; padding: 15px; margin: 10px 0; border-radius: 5px; border-left: 4px solid #4CAF50;'>"
            final_html += f"{final_result.get('answer', 'No final answer generated.')}"
            final_html += "</div>"

        current_html = self.chain_results.toHtml()
        self.chain_results.setHtml(current_html + final_html)

        self.statusBar().showMessage(f"Chain execution completed - {len(results)} steps")

    def chain_error(self, error_message: str):
        """Handle chain execution error"""
        self.run_chain_btn.setEnabled(True)
        QMessageBox.critical(self, "Chain Error", f"Chain execution failed: {error_message}")

    def save_settings(self):
        """Save settings to configuration"""
        try:
            # Update configuration
            if 'database_settings' not in self.config:
                self.config['database_settings'] = {}

            self.config['database_settings']['chunk_size'] = self.chunk_size_spin.value()
            self.config['database_settings']['chunk_overlap'] = self.chunk_overlap_spin.value()
            self.config['database_settings']['max_chunks_per_query'] = self.max_chunks_spin.value()

            if 'security_settings' not in self.config:
                self.config['security_settings'] = {}

            self.config['security_settings']['auto_lock_minutes'] = self.auto_lock_minutes.value()
            self.config['security_settings']['require_password_on_startup'] = self.auto_lock_check.isChecked()
            self.config['security_settings']['audit_logging'] = self.audit_log_check.isChecked()

            # Save to file
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=2)

            QMessageBox.information(self, "Success", "Settings saved successfully.")

        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to save settings: {e}")

    def reset_settings(self):
        """Reset settings to defaults"""
        self.chunk_size_spin.setValue(1000)
        self.chunk_overlap_spin.setValue(200)
        self.max_chunks_spin.setValue(5)
        self.auto_lock_minutes.setValue(30)
        self.auto_lock_check.setChecked(True)
        self.audit_log_check.setChecked(True)
