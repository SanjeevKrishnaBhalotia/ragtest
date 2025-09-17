"""
Prompt Workshop Component
Implements advanced prompt templating and chaining functionality
"""

import json
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from jinja2 import Template
from utils.logger import get_logger

logger = get_logger(__name__)

class PromptTemplate:
    """Individual prompt template with metadata"""

    def __init__(self, template_id: str = None, name: str = "", description: str = "", 
                 template_content: str = "", variables: List[str] = None, category: str = "General"):
        self.template_id = template_id or str(uuid.uuid4())
        self.name = name
        self.description = description
        self.template_content = template_content
        self.variables = variables or []
        self.category = category
        self.created_at = datetime.now().isoformat()
        self.modified_at = datetime.now().isoformat()

    def render(self, variables: Dict[str, Any]) -> str:
        """Render template with provided variables"""
        try:
            jinja_template = Template(self.template_content)
            return jinja_template.render(**variables)
        except Exception as e:
            logger.error(f"Failed to render template {self.name}: {e}")
            return f"Template rendering error: {e}"

class PromptChain:
    """Chain of prompt templates for sequential execution"""

    def __init__(self, chain_id: str = None, name: str = "", description: str = "",
                 steps: List[Dict[str, str]] = None):
        self.chain_id = chain_id or str(uuid.uuid4())
        self.name = name
        self.description = description
        self.steps = steps or []  # List of {'template_id': str, 'name': str}
        self.created_at = datetime.now().isoformat()

class PromptWorkshop:
    """Main prompt workshop manager with chaining support"""

    def __init__(self, prompts_dir: Path):
        self.prompts_dir = Path(prompts_dir)
        self.prompts_dir.mkdir(exist_ok=True)

        self.templates_file = self.prompts_dir / "templates.json"
        self.chains_file = self.prompts_dir / "chains.json"

        self.templates: Dict[str, PromptTemplate] = {}
        self.chains: Dict[str, PromptChain] = {}

        self.load_default_templates()
        logger.info("PromptWorkshop initialized")

    def load_default_templates(self):
        """Load default templates for immediate use"""
        if not self.templates:
            # Basic Q&A template
            basic_qa = PromptTemplate(
                name='Basic Q&A',
                description='Simple question answering with context',
                template_content="""Based on the following context, please answer the question.

Context:
{% for document in documents %}
{{ document.content }}
{% endfor %}

Question: {{ query }}

Answer:""",
                variables=['documents', 'query'],
                category='General'
            )
            self.templates[basic_qa.template_id] = basic_qa

            # Analysis template
            analysis = PromptTemplate(
                name='Detailed Analysis',
                description='In-depth analysis with structured response',
                template_content="""Please provide a detailed analysis:

Source Materials:
{% for document in documents %}
Source: {{ document.meta.source_database if document.meta else 'Unknown' }}
{{ document.content }}

{% endfor %}

Analysis Request: {{ query }}

Please provide:
1. Key findings
2. Detailed analysis
3. Supporting evidence
4. Conclusions

Analysis:""",
                variables=['documents', 'query'],
                category='Analysis'
            )
            self.templates[analysis.template_id] = analysis

            # Chain step 1: Extract
            extract = PromptTemplate(
                name='Step 1: Extract Information',
                description='Extract relevant information',
                template_content="""Extract all information relevant to: {{ query }}

Context:
{{ context }}

Extracted Information:""",
                variables=['query', 'context'],
                category='Chain'
            )
            self.templates[extract.template_id] = extract

            # Chain step 2: Analyze  
            analyze = PromptTemplate(
                name='Step 2: Analyze Information',
                description='Analyze extracted information',
                template_content="""Based on the extracted information, provide analysis:

Query: {{ query }}

Extracted Information:
{{ previous_answer }}

Analysis:""",
                variables=['query', 'previous_answer'],
                category='Chain'
            )
            self.templates[analyze.template_id] = analyze

            # Chain step 3: Recommend
            recommend = PromptTemplate(
                name='Step 3: Generate Recommendations',
                description='Provide actionable recommendations',
                template_content="""Based on the analysis, provide recommendations:

Original Query: {{ query }}

Analysis:
{{ previous_answer }}

Recommendations:""",
                variables=['query', 'previous_answer'],
                category='Chain'
            )
            self.templates[recommend.template_id] = recommend

            # Create default chain
            default_chain = PromptChain(
                name='Extract → Analyze → Recommend',
                description='Three-step analysis chain',
                steps=[
                    {'template_id': extract.template_id, 'name': extract.name},
                    {'template_id': analyze.template_id, 'name': analyze.name},
                    {'template_id': recommend.template_id, 'name': recommend.name}
                ]
            )
            self.chains[default_chain.chain_id] = default_chain

            logger.info("Created default templates and chains")

    def list_templates(self, category: str = None) -> List[PromptTemplate]:
        """List all templates, optionally filtered by category"""
        templates = list(self.templates.values())
        if category:
            templates = [t for t in templates if t.category == category]
        return sorted(templates, key=lambda x: x.name)

    def list_chains(self) -> List[PromptChain]:
        """List all chains"""
        return sorted(self.chains.values(), key=lambda x: x.name)

    def get_template(self, template_id: str) -> Optional[PromptTemplate]:
        """Get a template by ID"""
        return self.templates.get(template_id)

    def get_chain(self, chain_id: str) -> Optional[PromptChain]:
        """Get a chain by ID"""
        return self.chains.get(chain_id)

    def execute_chain(self, chain_id: str, initial_variables: Dict[str, Any], 
                     rag_pipeline, progress_callback=None) -> List[Dict[str, Any]]:
        """Execute a prompt chain with RAG pipeline integration"""
        chain = self.get_chain(chain_id)
        if not chain:
            raise ValueError(f"Chain {chain_id} not found")

        if not rag_pipeline or not rag_pipeline.current_model:
            raise ValueError("RAG pipeline not initialized or no model loaded")

        results = []
        current_variables = initial_variables.copy()

        for i, step in enumerate(chain.steps):
            try:
                if progress_callback:
                    progress_callback(f"[Chain {i+1}/{len(chain.steps)}] Executing: {step['name']}...")

                template = self.get_template(step['template_id'])
                if not template:
                    logger.error(f"Template {step['template_id']} not found in chain")
                    continue

                # Render the prompt
                prompt = template.render(current_variables)

                # Execute with RAG pipeline
                response = rag_pipeline.current_generator.run(prompt=prompt)
                answer = response['replies'][0] if response.get('replies') else 'No response generated.'

                # Store result
                step_result = {
                    'step_number': i + 1,
                    'step_name': step['name'],
                    'template_id': step['template_id'],
                    'prompt': prompt,
                    'answer': answer,
                    'timestamp': datetime.now().isoformat()
                }
                results.append(step_result)

                # Update variables for next step
                current_variables['previous_answer'] = answer
                current_variables[f'step_{i+1}_result'] = answer

                if progress_callback:
                    progress_callback(f"[Chain {i+1}/{len(chain.steps)}] ✓ Completed: {step['name']}")

            except Exception as e:
                logger.error(f"Failed to execute chain step {i+1}: {e}")
                step_result = {
                    'step_number': i + 1,
                    'step_name': step['name'],
                    'template_id': step['template_id'],
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }
                results.append(step_result)
                break

        return results
