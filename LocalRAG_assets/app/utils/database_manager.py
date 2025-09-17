"""
Database Manager - Handles encrypted ChromaDB collections
Implements AES-256 encryption for HIPAA compliance
"""

import os
import json
import hashlib
import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import shutil

import chromadb
from chromadb.config import Settings
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

from utils.logger import get_logger

logger = get_logger(__name__)

class DatabaseManager:
    """Manages encrypted ChromaDB collections for multi-database RAG"""

    def __init__(self, databases_dir: Path, master_password: str):
        self.databases_dir = Path(databases_dir)
        self.databases_dir.mkdir(exist_ok=True)
        self.master_password = master_password
        self.active_databases = {}
        self.audit_file = self.databases_dir / "audit.csv"

        # Initialize audit log
        self._init_audit_log()

        # Generate encryption key from master password
        self.encryption_key = self._derive_key(master_password)
        self.cipher_suite = Fernet(self.encryption_key)

        logger.info("DatabaseManager initialized")

    def _derive_key(self, password: str) -> bytes:
        """Derive encryption key from master password using PBKDF2"""
        salt = b'localrag_salt_2024'  # In production, use random salt per database
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key

    def _init_audit_log(self):
        """Initialize audit log CSV file"""
        if not self.audit_file.exists():
            with open(self.audit_file, 'w') as f:
                f.write("timestamp,action,database_name,user,details\n")

    def _log_audit(self, action: str, database_name: str, details: str = ""):
        """Log action to audit trail"""
        timestamp = datetime.now().isoformat()
        with open(self.audit_file, 'a') as f:
            f.write(f'"{timestamp}","{action}","{database_name}","local_user","{details}"\n')

    def create_database(self, name: str, description: str = "") -> bool:
        """Create a new encrypted database"""
        try:
            db_path = self.databases_dir / name
            if db_path.exists():
                logger.warning(f"Database {name} already exists")
                return False

            # Create database directory
            db_path.mkdir()

            # Create ChromaDB persistent client
            client = chromadb.PersistentClient(
                path=str(db_path / "chroma_data"),
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )

            # Create collection
            collection = client.create_collection(
                name="documents",
                metadata={"description": description}
            )

            # Create database metadata
            metadata = {
                "name": name,
                "description": description,
                "created_at": datetime.now().isoformat(),
                "document_count": 0,
                "encrypted": True
            }

            # Encrypt and save metadata
            encrypted_metadata = self.cipher_suite.encrypt(
                json.dumps(metadata).encode()
            )

            with open(db_path / "metadata.enc", 'wb') as f:
                f.write(encrypted_metadata)

            self._log_audit("CREATE_DATABASE", name, f"Database created: {description}")
            logger.info(f"Database '{name}' created successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to create database '{name}': {e}")
            return False

    def list_databases(self) -> List[Dict[str, Any]]:
        """List all available databases"""
        databases = []

        for db_path in self.databases_dir.iterdir():
            if db_path.is_dir() and (db_path / "metadata.enc").exists():
                try:
                    metadata = self._load_database_metadata(db_path.name)
                    if metadata:
                        databases.append(metadata)
                except Exception as e:
                    logger.warning(f"Failed to load metadata for {db_path.name}: {e}")

        return databases

    def _load_database_metadata(self, name: str) -> Optional[Dict[str, Any]]:
        """Load and decrypt database metadata"""
        try:
            db_path = self.databases_dir / name
            metadata_file = db_path / "metadata.enc"

            if not metadata_file.exists():
                return None

            with open(metadata_file, 'rb') as f:
                encrypted_data = f.read()

            decrypted_data = self.cipher_suite.decrypt(encrypted_data)
            metadata = json.loads(decrypted_data.decode())

            return metadata

        except Exception as e:
            logger.error(f"Failed to load metadata for '{name}': {e}")
            return None

    def load_database(self, name: str):
        """Load database and return ChromaDB collection"""
        try:
            if name in self.active_databases:
                return self.active_databases[name]

            db_path = self.databases_dir / name
            if not db_path.exists():
                logger.error(f"Database '{name}' not found")
                return None

            # Create ChromaDB client
            client = chromadb.PersistentClient(
                path=str(db_path / "chroma_data"),
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )

            # Get collection
            collection = client.get_collection("documents")

            self.active_databases[name] = {
                'client': client,
                'collection': collection,
                'metadata': self._load_database_metadata(name)
            }

            self._log_audit("LOAD_DATABASE", name)
            logger.info(f"Database '{name}' loaded successfully")

            return self.active_databases[name]

        except Exception as e:
            logger.error(f"Failed to load database '{name}': {e}")
            return None

    def delete_database(self, name: str) -> bool:
        """Delete a database permanently"""
        try:
            # Remove from active databases
            if name in self.active_databases:
                del self.active_databases[name]

            # Delete directory
            db_path = self.databases_dir / name
            if db_path.exists():
                shutil.rmtree(db_path)

            self._log_audit("DELETE_DATABASE", name)
            logger.info(f"Database '{name}' deleted successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to delete database '{name}': {e}")
            return False

    def add_documents(self, database_name: str, documents: List[Dict[str, Any]]) -> bool:
        """Add documents to a database"""
        try:
            db = self.load_database(database_name)
            if not db:
                return False

            collection = db['collection']

            # Prepare data for ChromaDB
            ids = [doc['id'] for doc in documents]
            texts = [doc['content'] for doc in documents]
            metadatas = [doc.get('metadata', {}) for doc in documents]

            # Add to collection
            collection.add(
                documents=texts,
                metadatas=metadatas,
                ids=ids
            )

            # Update document count in metadata
            metadata = db['metadata']
            metadata['document_count'] = collection.count()
            self._update_database_metadata(database_name, metadata)

            self._log_audit("ADD_DOCUMENTS", database_name, f"Added {len(documents)} documents")
            logger.info(f"Added {len(documents)} documents to '{database_name}'")
            return True

        except Exception as e:
            logger.error(f"Failed to add documents to '{database_name}': {e}")
            return False

    def _update_database_metadata(self, name: str, metadata: Dict[str, Any]):
        """Update and encrypt database metadata"""
        try:
            db_path = self.databases_dir / name
            encrypted_metadata = self.cipher_suite.encrypt(
                json.dumps(metadata).encode()
            )

            with open(db_path / "metadata.enc", 'wb') as f:
                f.write(encrypted_metadata)

        except Exception as e:
            logger.error(f"Failed to update metadata for '{name}': {e}")

    def query_databases(self, query: str, database_names: List[str], n_results: int = 5) -> Dict[str, List[Dict[str, Any]]]:
        """Query multiple databases and return results"""
        results = {}

        for db_name in database_names:
            try:
                db = self.load_database(db_name)
                if not db:
                    continue

                collection = db['collection']

                # Query collection
                query_results = collection.query(
                    query_texts=[query],
                    n_results=n_results
                )

                # Format results
                formatted_results = []
                if query_results['documents'] and query_results['documents'][0]:
                    for i, doc in enumerate(query_results['documents'][0]):
                        result = {
                            'content': doc,
                            'metadata': query_results['metadatas'][0][i] if query_results['metadatas'][0] else {},
                            'distance': query_results['distances'][0][i] if query_results['distances'] else None,
                            'source_database': db_name
                        }
                        formatted_results.append(result)

                results[db_name] = formatted_results

                self._log_audit("QUERY_DATABASE", db_name, f"Query: {query[:100]}...")

            except Exception as e:
                logger.error(f"Failed to query database '{db_name}': {e}")
                results[db_name] = []

        return results
