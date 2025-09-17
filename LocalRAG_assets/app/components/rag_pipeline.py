"""
RAG Pipeline Component using Haystack
Implements retrieval-augmented generation with swappable LLMs
"""

import os
from pathlib import Path
from typing import List, Dict, Any, Optional
import json

from haystack import Document
from haystack.components.generators import LlamaCppGenerator
from sentence_transformers import SentenceTransformer

from utils.logger import get_logger
from utils.database_manager import DatabaseManager

logger = get_logger(__name__)

class RAGPipeline:
    """Main RAG pipeline with swappable LLM support"""

    def __init__(self, config_path: Path, databases_dir: Path, models_dir: Path):
        self.config_path = config_path
        self.databases_dir = databases_dir 
        self.models_dir = models_dir

        # Load configuration
        with open(config_path, 'r') as f:
            self.config = json.load(f)

        self.current_model = None
        self.current_generator = None
        self.embedding_model = None
        self.database_manager = None

        # Initialize embedding model
        self._init_embedding_model()

        logger.info("RAGPipeline initialized")

    def _init_embedding_model(self):
        """Initialize the embedding model"""
        try:
            model_name = self.config['database_settings']['embedding_model']
            self.embedding_model = SentenceTransformer(model_name)
            logger.info(f"Embedding model '{model_name}' loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise

    def set_master_password(self, password: str):
        """Set master password and initialize database manager"""
        self.database_manager = DatabaseManager(self.databases_dir, password)
        logger.info("Database manager initialized with master password")

    def load_model(self, model_name: str) -> bool:
        """Load a specific LLM model"""
        try:
            # Find model configuration
            model_config = None
            for model in self.config['models']:
                if model['name'] == model_name:
                    model_config = model
                    break

            if not model_config:
                logger.error(f"Model '{model_name}' not found in configuration")
                return False

            model_path = self.models_dir / model_config['file_path']
            if not model_path.exists():
                logger.error(f"Model file not found: {model_path}")
                return False

            # Create LlamaCpp generator
            self.current_generator = LlamaCppGenerator(
                model=str(model_path),
                n_ctx=model_config.get('context_length', 4096),
                n_batch=512,
                model_kwargs={
                    "n_threads": os.cpu_count(),
                    "verbose": False
                }
            )

            self.current_model = model_config
            logger.info(f"Model '{model_name}' loaded successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to load model '{model_name}': {e}")
            return False

    def get_available_models(self) -> List[Dict[str, Any]]:
        """Get list of available models with their status"""
        models = []

        for model in self.config['models']:
            model_path = self.models_dir / model['file_path']
            model_info = {
                'name': model['name'],
                'size_gb': model['size_gb'],
                'ram_required_gb': model['ram_required_gb'],
                'context_length': model['context_length'],
                'available': model_path.exists(),
                'download_url': model.get('download_url', ''),
                'file_path': str(model_path)
            }
            models.append(model_info)

        return models

    def query_single_database(self, query: str, database_name: str, progress_callback=None) -> Dict[str, Any]:
        """Query a single database"""
        try:
            if progress_callback:
                progress_callback("[1/6] Loading database...")

            # Get database documents using database manager
            db_results = self.database_manager.query_databases(
                query, 
                [database_name], 
                n_results=self.config['database_settings']['max_chunks_per_query']
            )

            if not db_results.get(database_name):
                return {
                    'answer': 'No relevant documents found in the database.',
                    'sources': [],
                    'confidence': 0.0,
                    'model_used': self.current_model['name']
                }

            if progress_callback:
                progress_callback("[2/6] Preparing context...")

            # Convert to context format
            documents = db_results[database_name]

            if progress_callback:
                progress_callback("[3/6] Building prompt...")

            # Create prompt template
            prompt_template = self.current_model['prompt_template']
            system_message = self.current_model['system_message']

            context = "\n".join([doc['content'] for doc in documents])

            prompt = prompt_template.format(
                system_message=system_message + f"\n\nContext:\n{context}",
                user_message=query
            )

            if progress_callback:
                progress_callback("[4/6] Generating answer (this may take a moment)...")

            # Generate response
            response = self.current_generator.run(prompt=prompt)

            if progress_callback:
                progress_callback("[5/6] Processing response...")

            # Calculate confidence (simple heuristic based on context relevance)
            confidence = min(len(documents) * 0.2, 1.0)

            # Prepare sources
            sources = []
            for doc in documents:
                source_info = {
                    'database': doc.get('source_database', database_name),
                    'content_preview': doc['content'][:200] + "..." if len(doc['content']) > 200 else doc['content'],
                    'metadata': doc.get('metadata', {})
                }
                sources.append(source_info)

            if progress_callback:
                progress_callback("[6/6] Complete!")

            return {
                'answer': response['replies'][0] if response.get('replies') else 'No response generated.',
                'sources': sources,
                'confidence': confidence,
                'model_used': self.current_model['name'],
                'databases_queried': [database_name]
            }

        except Exception as e:
            logger.error(f"Failed to query database '{database_name}': {e}")
            return {
                'answer': f'Error occurred during query: {str(e)}',
                'sources': [],
                'confidence': 0.0,
                'model_used': self.current_model['name'] if self.current_model else 'None'
            }

    def query_multiple_databases(self, query: str, database_names: List[str], progress_callback=None) -> Dict[str, Any]:
        """Query multiple databases with re-ranking"""
        try:
            if progress_callback:
                progress_callback(f"[1/7] Querying {len(database_names)} databases...")

            # Query all databases
            all_results = self.database_manager.query_databases(
                query, 
                database_names, 
                n_results=self.config['database_settings']['max_chunks_per_query']
            )

            if progress_callback:
                progress_callback("[2/7] Collecting results...")

            # Combine all results
            all_documents = []
            for db_name, results in all_results.items():
                all_documents.extend(results)

            if not all_documents:
                return {
                    'answer': 'No relevant documents found in any of the selected databases.',
                    'sources': [],
                    'confidence': 0.0,
                    'model_used': self.current_model['name'],
                    'databases_queried': database_names
                }

            if progress_callback:
                progress_callback("[3/7] Re-ranking results for accuracy...")

            # Simple re-ranking by distance (lower is better)
            all_documents.sort(key=lambda doc: doc.get('distance', 1.0))

            # Take top results
            max_chunks = self.config['database_settings']['max_chunks_per_query']
            top_documents = all_documents[:max_chunks]

            if progress_callback:
                progress_callback("[4/7] Building comprehensive prompt...")

            # Create prompt template
            prompt_template = self.current_model['prompt_template']
            system_message = self.current_model['system_message']

            context_parts = []
            for doc in top_documents:
                db_name = doc.get('source_database', 'Unknown')
                context_parts.append(f"Source: {db_name}\n{doc['content']}")

            context = "\n\n".join(context_parts)

            prompt = prompt_template.format(
                system_message=system_message + f"\n\nContext from multiple sources:\n{context}",
                user_message=query
            )

            if progress_callback:
                progress_callback("[5/7] Generating answer (this may take a moment)...")

            # Generate response
            response = self.current_generator.run(prompt=prompt)

            if progress_callback:
                progress_callback("[6/7] Finalizing response...")

            # Calculate confidence
            confidence = min(len(top_documents) * 0.15 + len(database_names) * 0.1, 1.0)

            # Prepare sources
            sources = []
            for doc in top_documents:
                source_info = {
                    'database': doc.get('source_database', 'Unknown'),
                    'content_preview': doc['content'][:200] + "..." if len(doc['content']) > 200 else doc['content'],
                    'metadata': doc.get('metadata', {})
                }
                sources.append(source_info)

            if progress_callback:
                progress_callback("[7/7] Complete!")

            return {
                'answer': response['replies'][0] if response.get('replies') else 'No response generated.',
                'sources': sources,
                'confidence': confidence,
                'model_used': self.current_model['name'],
                'databases_queried': database_names
            }

        except Exception as e:
            logger.error(f"Failed to query multiple databases: {e}")
            return {
                'answer': f'Error occurred during multi-database query: {str(e)}',
                'sources': [],
                'confidence': 0.0,
                'model_used': self.current_model['name'] if self.current_model else 'None',
                'databases_queried': database_names
            }
