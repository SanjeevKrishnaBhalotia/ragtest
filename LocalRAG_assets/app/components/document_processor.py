"""
Document Processor Component
Handles ingestion and chunking of various document types
"""

import os
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
import hashlib
import uuid
from datetime import datetime

import pandas as pd
from PyPDF2 import PdfReader
from docx import Document as DocxDocument
import openpyxl

from utils.logger import get_logger

logger = get_logger(__name__)

class DocumentProcessor:
    """Processes various document types for RAG ingestion"""

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def process_file(self, file_path: Path, chunking_mode: str = "general", metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Process a file and return list of document chunks"""
        try:
            file_extension = file_path.suffix.lower()

            if file_extension == '.pdf':
                return self._process_pdf(file_path, chunking_mode, metadata)
            elif file_extension == '.docx':
                return self._process_docx(file_path, chunking_mode, metadata)
            elif file_extension == '.txt':
                return self._process_txt(file_path, chunking_mode, metadata)
            elif file_extension == '.csv':
                return self._process_csv(file_path, metadata)
            elif file_extension in ['.xlsx', '.xls']:
                return self._process_excel(file_path, metadata)
            else:
                logger.warning(f"Unsupported file type: {file_extension}")
                return []

        except Exception as e:
            logger.error(f"Failed to process file {file_path}: {e}")
            return []

    def _process_pdf(self, file_path: Path, chunking_mode: str, metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Process PDF file"""
        documents = []

        try:
            reader = PdfReader(file_path)
            full_text = ""

            for page_num, page in enumerate(reader.pages):
                page_text = page.extract_text()
                full_text += f"\n\n--- Page {page_num + 1} ---\n{page_text}"

            # Apply chunking strategy
            chunks = self._apply_chunking_strategy(full_text, chunking_mode)

            # Create document objects
            for i, chunk in enumerate(chunks):
                doc_id = self._generate_document_id(file_path, i)
                doc_metadata = {
                    'source_file': str(file_path.name),
                    'source_type': 'pdf',
                    'chunk_index': i,
                    'total_chunks': len(chunks),
                    'processed_at': datetime.now().isoformat(),
                    **(metadata or {})
                }

                documents.append({
                    'id': doc_id,
                    'content': chunk,
                    'metadata': doc_metadata
                })

            logger.info(f"Processed PDF '{file_path.name}' into {len(documents)} chunks")
            return documents

        except Exception as e:
            logger.error(f"Failed to process PDF {file_path}: {e}")
            return []

    def _process_docx(self, file_path: Path, chunking_mode: str, metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Process DOCX file"""
        documents = []

        try:
            doc = DocxDocument(file_path)
            full_text = ""

            for paragraph in doc.paragraphs:
                full_text += paragraph.text + "\n"

            # Apply chunking strategy
            chunks = self._apply_chunking_strategy(full_text, chunking_mode)

            # Create document objects
            for i, chunk in enumerate(chunks):
                doc_id = self._generate_document_id(file_path, i)
                doc_metadata = {
                    'source_file': str(file_path.name),
                    'source_type': 'docx',
                    'chunk_index': i,
                    'total_chunks': len(chunks),
                    'processed_at': datetime.now().isoformat(),
                    **(metadata or {})
                }

                documents.append({
                    'id': doc_id,
                    'content': chunk,
                    'metadata': doc_metadata
                })

            logger.info(f"Processed DOCX '{file_path.name}' into {len(documents)} chunks")
            return documents

        except Exception as e:
            logger.error(f"Failed to process DOCX {file_path}: {e}")
            return []

    def _process_txt(self, file_path: Path, chunking_mode: str, metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Process TXT file"""
        documents = []

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                full_text = f.read()

            # Apply chunking strategy
            chunks = self._apply_chunking_strategy(full_text, chunking_mode)

            # Create document objects
            for i, chunk in enumerate(chunks):
                doc_id = self._generate_document_id(file_path, i)
                doc_metadata = {
                    'source_file': str(file_path.name),
                    'source_type': 'txt',
                    'chunk_index': i,
                    'total_chunks': len(chunks),
                    'processed_at': datetime.now().isoformat(),
                    **(metadata or {})
                }

                documents.append({
                    'id': doc_id,
                    'content': chunk,
                    'metadata': doc_metadata
                })

            logger.info(f"Processed TXT '{file_path.name}' into {len(documents)} chunks")
            return documents

        except Exception as e:
            logger.error(f"Failed to process TXT {file_path}: {e}")
            return []

    def _process_csv(self, file_path: Path, metadata: Optional[Dict[str, Any]] = None, column_mapping: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
        """Process CSV file with column mapping"""
        documents = []

        try:
            df = pd.read_csv(file_path)

            # Default column mapping if not provided
            if not column_mapping:
                content_col = df.columns[0] if len(df.columns) > 0 else None
                if not content_col:
                    logger.error(f"CSV file {file_path} has no columns")
                    return []
                column_mapping = {'content': content_col}

            content_column = column_mapping.get('content')
            if content_column not in df.columns:
                logger.error(f"Content column '{content_column}' not found in CSV")
                return []

            # Process each row
            for index, row in df.iterrows():
                content = str(row[content_column])

                if pd.isna(content) or content.strip() == '':
                    continue

                doc_id = self._generate_document_id(file_path, index)

                # Build metadata from other columns
                row_metadata = {
                    'source_file': str(file_path.name),
                    'source_type': 'csv',
                    'row_number': int(index) + 1,
                    'processed_at': datetime.now().isoformat(),
                    **(metadata or {})
                }

                # Add other columns as metadata
                for col in df.columns:
                    if col != content_column and col not in column_mapping.values():
                        row_metadata[f'csv_{col}'] = str(row[col]) if not pd.isna(row[col]) else ''

                documents.append({
                    'id': doc_id, 
                    'content': content,
                    'metadata': row_metadata
                })

            logger.info(f"Processed CSV '{file_path.name}' into {len(documents)} documents")
            return documents

        except Exception as e:
            logger.error(f"Failed to process CSV {file_path}: {e}")
            return []

    def _process_excel(self, file_path: Path, metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Process Excel file"""
        documents = []

        try:
            # Read all sheets
            xl_file = pd.ExcelFile(file_path)

            for sheet_name in xl_file.sheet_names:
                df = pd.read_excel(file_path, sheet_name=sheet_name)

                # Use first column as content
                if len(df.columns) == 0:
                    continue

                content_column = df.columns[0]

                for index, row in df.iterrows():
                    content = str(row[content_column])

                    if pd.isna(content) or content.strip() == '':
                        continue

                    doc_id = self._generate_document_id(file_path, f"{sheet_name}_{index}")

                    row_metadata = {
                        'source_file': str(file_path.name),
                        'source_type': 'excel',
                        'sheet_name': sheet_name,
                        'row_number': int(index) + 1,
                        'processed_at': datetime.now().isoformat(),
                        **(metadata or {})
                    }

                    # Add other columns as metadata
                    for col in df.columns:
                        if col != content_column:
                            row_metadata[f'excel_{col}'] = str(row[col]) if not pd.isna(row[col]) else ''

                    documents.append({
                        'id': doc_id,
                        'content': content,
                        'metadata': row_metadata
                    })

            logger.info(f"Processed Excel '{file_path.name}' into {len(documents)} documents")
            return documents

        except Exception as e:
            logger.error(f"Failed to process Excel {file_path}: {e}")
            return []

    def _apply_chunking_strategy(self, text: str, chunking_mode: str) -> List[str]:
        """Apply different chunking strategies based on mode"""

        if chunking_mode == "statute":
            return self._chunk_legal_text(text)
        elif chunking_mode == "letter":
            return self._chunk_letter_text(text)
        else:
            return self._chunk_general_text(text)

    def _chunk_general_text(self, text: str) -> List[str]:
        """General recursive character-based chunking"""
        if len(text) <= self.chunk_size:
            return [text]

        chunks = []
        start = 0

        while start < len(text):
            end = start + self.chunk_size

            if end >= len(text):
                chunks.append(text[start:])
                break

            # Try to break at sentence boundary
            chunk = text[start:end]
            last_period = chunk.rfind('.')
            last_newline = chunk.rfind('\n')

            best_break = max(last_period, last_newline)

            if best_break > start + self.chunk_size // 2:
                end = start + best_break + 1

            chunks.append(text[start:end])
            start = end - self.chunk_overlap

        return [chunk.strip() for chunk in chunks if chunk.strip()]

    def _chunk_legal_text(self, text: str) -> List[str]:
        """Legal document chunking based on sections and citations"""

        # Patterns for legal sections
        section_patterns = [
            r'§\s*\d+[\w.-]*',  # Section symbols
            r'Section\s+\d+[\w.-]*',  # Section word
            r'Article\s+[IVX]+',  # Articles
            r'Chapter\s+\d+',  # Chapters
            r'\b\d+\s*CFR\s*\d+',  # CFR citations
        ]

        combined_pattern = '|'.join(section_patterns)

        # Split on legal section boundaries
        sections = re.split(f'({combined_pattern})', text, flags=re.IGNORECASE)

        chunks = []
        current_chunk = ""

        for section in sections:
            if re.match(combined_pattern, section, re.IGNORECASE):
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = section + " "
            else:
                current_chunk += section

                # If chunk gets too long, apply general chunking
                if len(current_chunk) > self.chunk_size * 2:
                    sub_chunks = self._chunk_general_text(current_chunk)
                    chunks.extend(sub_chunks[:-1])
                    current_chunk = sub_chunks[-1] if sub_chunks else ""

        if current_chunk:
            chunks.append(current_chunk.strip())

        return [chunk for chunk in chunks if chunk.strip()]

    def _chunk_letter_text(self, text: str) -> List[str]:
        """Letter/document chunking based on paragraphs and page breaks"""

        # Split by page breaks first
        pages = text.split('--- Page ')

        chunks = []

        for page in pages:
            if not page.strip():
                continue

            # Split by numbered paragraphs
            paragraphs = re.split(r'\n\s*\d+\.\s+', page)

            for paragraph in paragraphs:
                paragraph = paragraph.strip()
                if not paragraph:
                    continue

                # If paragraph is too long, apply general chunking
                if len(paragraph) > self.chunk_size:
                    sub_chunks = self._chunk_general_text(paragraph)
                    chunks.extend(sub_chunks)
                else:
                    chunks.append(paragraph)

        return chunks

    def _generate_document_id(self, file_path: Path, suffix: Any) -> str:
        """Generate unique document ID"""
        source = f"{file_path.name}_{suffix}"
        return hashlib.md5(source.encode()).hexdigest()

    def get_supported_extensions(self) -> List[str]:
        """Get list of supported file extensions"""
        return ['.pdf', '.docx', '.txt', '.csv', '.xlsx', '.xls']

    def validate_file(self, file_path: Path) -> Dict[str, Any]:
        """Validate file before processing"""
        result = {
            'valid': False,
            'error': None,
            'size_mb': 0,
            'extension': file_path.suffix.lower()
        }

        try:
            if not file_path.exists():
                result['error'] = "File does not exist"
                return result

            if file_path.suffix.lower() not in self.get_supported_extensions():
                result['error'] = f"Unsupported file type: {file_path.suffix}"
                return result

            file_size = file_path.stat().st_size
            size_mb = file_size / (1024 * 1024)
            result['size_mb'] = round(size_mb, 2)

            if size_mb > 100:  # 100MB limit
                result['error'] = f"File too large: {size_mb:.1f}MB (max 100MB)"
                return result

            result['valid'] = True
            return result

        except Exception as e:
            result['error'] = f"Validation error: {str(e)}"
            return result
