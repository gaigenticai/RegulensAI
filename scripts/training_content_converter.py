#!/usr/bin/env python3
"""
Training Content Converter for RegulensAI Training Portal.
Converts existing markdown training files into interactive web portal format.
"""

import os
import re
import json
import yaml
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
import markdown
from markdown.extensions import codehilite, toc, tables
import structlog

logger = structlog.get_logger(__name__)


class TrainingContentConverter:
    """
    Converts markdown training content into interactive web portal format.
    """
    
    def __init__(self, input_dir: str = "docs/training", output_dir: str = "database/training_content"):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.markdown_processor = markdown.Markdown(
            extensions=['codehilite', 'toc', 'tables', 'fenced_code']
        )
        
        # Training module configurations
        self.module_configs = {
            "notification_management_guide.md": {
                "module_code": "notification_management",
                "title": "Notification Management Training",
                "category": "notification_management",
                "difficulty_level": "intermediate",
                "estimated_duration_minutes": 120,
                "learning_objectives": [
                    "Create and manage notification templates",
                    "Configure notification channels",
                    "Send bulk notifications efficiently",
                    "Monitor notification delivery and performance",
                    "Troubleshoot common notification issues"
                ],
                "prerequisites": ["api_usage_basics"],
                "is_mandatory": True
            },
            "external_data_provider_training.md": {
                "module_code": "external_data_providers",
                "title": "External Data Provider Integration",
                "category": "external_data",
                "difficulty_level": "advanced",
                "estimated_duration_minutes": 180,
                "learning_objectives": [
                    "Configure external data provider connections",
                    "Perform entity screening across multiple providers",
                    "Manage data updates and synchronization",
                    "Monitor provider performance and availability",
                    "Troubleshoot common integration issues"
                ],
                "prerequisites": ["notification_management"],
                "is_mandatory": True
            },
            "operational_procedures_training.md": {
                "module_code": "operational_procedures",
                "title": "Operational Procedures Training",
                "category": "operational_procedures",
                "difficulty_level": "expert",
                "estimated_duration_minutes": 240,
                "learning_objectives": [
                    "Perform routine system administration tasks",
                    "Monitor system health and performance",
                    "Respond to incidents effectively",
                    "Execute backup and recovery procedures",
                    "Manage security operations"
                ],
                "prerequisites": ["external_data_providers"],
                "is_mandatory": True
            }
        }
    
    def convert_all_training_files(self) -> List[Dict[str, Any]]:
        """Convert all training markdown files to interactive format."""
        converted_modules = []
        
        for filename, config in self.module_configs.items():
            filepath = os.path.join(self.input_dir, filename)
            
            if os.path.exists(filepath):
                logger.info(f"Converting {filename}")
                module_data = self.convert_training_file(filepath, config)
                converted_modules.append(module_data)
            else:
                logger.warning(f"Training file not found: {filepath}")
        
        # Save converted modules
        self.save_converted_modules(converted_modules)
        
        return converted_modules
    
    def convert_training_file(self, filepath: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Convert a single training markdown file."""
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse the markdown content
        sections = self.parse_markdown_sections(content)
        
        # Create module data
        module_data = {
            "id": str(uuid.uuid4()),
            "module_code": config["module_code"],
            "title": config["title"],
            "description": self.extract_description(content),
            "category": config["category"],
            "difficulty_level": config["difficulty_level"],
            "estimated_duration_minutes": config["estimated_duration_minutes"],
            "learning_objectives": config["learning_objectives"],
            "prerequisites": config.get("prerequisites", []),
            "content_type": "interactive",
            "is_mandatory": config.get("is_mandatory", False),
            "is_active": True,
            "version": "1.0",
            "sections": sections,
            "assessments": self.create_assessments(sections, config),
            "created_at": datetime.utcnow().isoformat()
        }
        
        return module_data
    
    def parse_markdown_sections(self, content: str) -> List[Dict[str, Any]]:
        """Parse markdown content into sections."""
        # Split content by main headings (## level)
        section_pattern = r'^## (.+)$'
        sections = []
        
        # Find all section headers
        section_matches = list(re.finditer(section_pattern, content, re.MULTILINE))
        
        for i, match in enumerate(section_matches):
            section_title = match.group(1).strip()
            section_start = match.end()
            
            # Find the end of this section (start of next section or end of content)
            if i + 1 < len(section_matches):
                section_end = section_matches[i + 1].start()
            else:
                section_end = len(content)
            
            section_content = content[section_start:section_end].strip()
            
            # Skip empty sections
            if not section_content:
                continue
            
            # Process section content
            section_data = self.process_section_content(section_title, section_content, i + 1)
            sections.append(section_data)
        
        return sections
    
    def process_section_content(self, title: str, content: str, order: int) -> Dict[str, Any]:
        """Process individual section content."""
        # Generate section code from title
        section_code = re.sub(r'[^a-zA-Z0-9]', '_', title.lower()).strip('_')
        
        # Extract interactive elements
        interactive_elements = self.extract_interactive_elements(content)
        
        # Convert markdown to HTML
        html_content = self.markdown_processor.convert(content)
        
        # Estimate duration based on content length and complexity
        estimated_duration = self.estimate_section_duration(content, interactive_elements)
        
        return {
            "id": str(uuid.uuid4()),
            "section_code": section_code,
            "title": title,
            "description": self.extract_section_description(content),
            "content_markdown": content,
            "content_html": html_content,
            "section_order": order,
            "estimated_duration_minutes": estimated_duration,
            "is_interactive": bool(interactive_elements),
            "interactive_elements": interactive_elements,
            "is_required": True
        }
    
    def extract_interactive_elements(self, content: str) -> Dict[str, Any]:
        """Extract interactive elements from section content."""
        elements = {}
        
        # Extract code blocks
        code_blocks = re.findall(r'```(\w+)?\n(.*?)\n```', content, re.DOTALL)
        if code_blocks:
            elements["exercises"] = []
            for i, (language, code) in enumerate(code_blocks):
                if language and code.strip():
                    elements["exercises"].append({
                        "id": f"code_exercise_{i}",
                        "type": "code",
                        "title": f"Code Example {i + 1}",
                        "description": "Try running this code example",
                        "language": language or "text",
                        "code": code.strip()
                    })
        
        # Extract checklists (lines starting with - [ ])
        checklist_items = re.findall(r'- \[ \] (.+)', content)
        if checklist_items:
            if "exercises" not in elements:
                elements["exercises"] = []
            elements["exercises"].append({
                "id": "checklist_exercise",
                "type": "checklist",
                "title": "Practice Checklist",
                "description": "Complete these hands-on tasks",
                "steps": checklist_items
            })
        
        # Extract key points (### Key Points or similar)
        key_points_match = re.search(r'### Key Points.*?\n(.*?)(?=\n###|\n##|\Z)', content, re.DOTALL)
        if key_points_match:
            key_points_content = key_points_match.group(1)
            key_points = re.findall(r'- (.+)', key_points_content)
            if key_points:
                elements["keyPoints"] = key_points
        
        # Extract best practices
        best_practices_match = re.search(r'### Best Practices.*?\n(.*?)(?=\n###|\n##|\Z)', content, re.DOTALL)
        if best_practices_match:
            best_practices_content = best_practices_match.group(1)
            best_practices = re.findall(r'- (.+)', best_practices_content)
            if best_practices:
                elements["bestPractices"] = best_practices
        
        # Extract common pitfalls/troubleshooting
        pitfalls_match = re.search(r'### (?:Common Issues|Troubleshooting|Common Pitfalls).*?\n(.*?)(?=\n###|\n##|\Z)', content, re.DOTALL)
        if pitfalls_match:
            pitfalls_content = pitfalls_match.group(1)
            pitfalls = re.findall(r'- (.+)', pitfalls_content)
            if pitfalls:
                elements["commonPitfalls"] = pitfalls
        
        # Create quiz questions based on content
        quiz_questions = self.generate_quiz_questions(content)
        if quiz_questions:
            elements["quiz"] = {
                "questions": quiz_questions,
                "passing_score": 80,
                "max_attempts": 3
            }
        
        return elements
    
    def generate_quiz_questions(self, content: str) -> List[Dict[str, Any]]:
        """Generate quiz questions based on section content."""
        questions = []
        
        # Look for numbered lists that could be converted to questions
        numbered_lists = re.findall(r'\d+\.\s+(.+)', content)
        
        # Look for important concepts (bold text)
        important_concepts = re.findall(r'\*\*(.+?)\*\*', content)
        
        # Generate multiple choice questions from important concepts
        for i, concept in enumerate(important_concepts[:3]):  # Limit to 3 questions
            if len(concept) > 10:  # Only use substantial concepts
                questions.append({
                    "id": f"question_{i + 1}",
                    "type": "multiple_choice",
                    "question": f"What is the purpose of {concept}?",
                    "options": [
                        {"id": "a", "text": f"To manage {concept.lower()}", "correct": True},
                        {"id": "b", "text": "To handle user authentication", "correct": False},
                        {"id": "c", "text": "To process payments", "correct": False},
                        {"id": "d", "text": "To generate reports", "correct": False}
                    ],
                    "explanation": f"This question tests understanding of {concept}."
                })
        
        # Add a text question for practical application
        if len(questions) < 5:
            questions.append({
                "id": "practical_question",
                "type": "text",
                "question": "Describe a real-world scenario where you would apply the concepts learned in this section.",
                "sample_answer": "Students should provide a specific example demonstrating understanding of the key concepts.",
                "points": 10
            })
        
        return questions
    
    def create_assessments(self, sections: List[Dict[str, Any]], config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create assessments for the module."""
        assessments = []
        
        # Create a final module assessment
        all_questions = []
        for section in sections:
            if section.get("interactive_elements", {}).get("quiz", {}).get("questions"):
                all_questions.extend(section["interactive_elements"]["quiz"]["questions"])
        
        if all_questions:
            assessments.append({
                "id": str(uuid.uuid4()),
                "assessment_code": f"{config['module_code']}_final_assessment",
                "title": f"{config['title']} - Final Assessment",
                "description": "Comprehensive assessment covering all module topics",
                "assessment_type": "quiz",
                "passing_score": 80,
                "max_attempts": 3,
                "time_limit_minutes": 30,
                "questions": all_questions[:10],  # Limit to 10 questions
                "is_required": True,
                "is_active": True
            })
        
        return assessments
    
    def extract_description(self, content: str) -> str:
        """Extract module description from content."""
        # Look for the first paragraph after the title
        lines = content.split('\n')
        description_lines = []
        
        found_title = False
        for line in lines:
            line = line.strip()
            if line.startswith('# '):
                found_title = True
                continue
            
            if found_title and line and not line.startswith('#'):
                description_lines.append(line)
                if len(description_lines) >= 3:  # Limit to first few lines
                    break
        
        return ' '.join(description_lines)
    
    def extract_section_description(self, content: str) -> str:
        """Extract section description from content."""
        # Get the first paragraph
        paragraphs = content.split('\n\n')
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if paragraph and not paragraph.startswith('#') and not paragraph.startswith('```'):
                # Clean up markdown formatting
                clean_paragraph = re.sub(r'\*\*(.+?)\*\*', r'\1', paragraph)
                clean_paragraph = re.sub(r'\*(.+?)\*', r'\1', clean_paragraph)
                return clean_paragraph[:200] + '...' if len(clean_paragraph) > 200 else clean_paragraph
        
        return "Training section content"
    
    def estimate_section_duration(self, content: str, interactive_elements: Dict[str, Any]) -> int:
        """Estimate section duration based on content and interactive elements."""
        # Base duration on word count (average reading speed: 200 words/minute)
        word_count = len(content.split())
        reading_time = max(5, word_count // 200)
        
        # Add time for interactive elements
        interactive_time = 0
        if interactive_elements.get("exercises"):
            interactive_time += len(interactive_elements["exercises"]) * 5
        
        if interactive_elements.get("quiz"):
            interactive_time += len(interactive_elements["quiz"]["questions"]) * 2
        
        return reading_time + interactive_time
    
    def save_converted_modules(self, modules: List[Dict[str, Any]]):
        """Save converted modules to JSON files."""
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Save individual module files
        for module in modules:
            filename = f"{module['module_code']}.json"
            filepath = os.path.join(self.output_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(module, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved converted module: {filepath}")
        
        # Save combined modules file
        combined_filepath = os.path.join(self.output_dir, "all_modules.json")
        with open(combined_filepath, 'w', encoding='utf-8') as f:
            json.dump(modules, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved combined modules file: {combined_filepath}")
        
        # Generate SQL insert statements
        self.generate_sql_inserts(modules)
    
    def generate_sql_inserts(self, modules: List[Dict[str, Any]]):
        """Generate SQL insert statements for the training portal database."""
        sql_file = os.path.join(self.output_dir, "training_content_inserts.sql")
        
        with open(sql_file, 'w', encoding='utf-8') as f:
            f.write("-- Training Content Insert Statements\n")
            f.write("-- Generated by TrainingContentConverter\n\n")
            
            # Insert modules
            f.write("-- Insert training modules\n")
            for module in modules:
                f.write(f"""
INSERT INTO public.training_modules (
    id, module_code, title, description, category, difficulty_level,
    estimated_duration_minutes, prerequisites, learning_objectives,
    content_type, is_mandatory, is_active, version, created_by, created_at
) VALUES (
    '{module['id']}',
    '{module['module_code']}',
    '{module['title'].replace("'", "''")}',
    '{module['description'].replace("'", "''")}',
    '{module['category']}',
    '{module['difficulty_level']}',
    {module['estimated_duration_minutes']},
    '{json.dumps(module['prerequisites'])}',
    '{json.dumps(module['learning_objectives'])}',
    '{module['content_type']}',
    {str(module['is_mandatory']).lower()},
    {str(module['is_active']).lower()},
    '{module['version']}',
    (SELECT id FROM public.users WHERE email = 'system@regulensai.com' LIMIT 1),
    '{module['created_at']}'
);
""")
            
            # Insert sections
            f.write("\n-- Insert training sections\n")
            for module in modules:
                for section in module['sections']:
                    f.write(f"""
INSERT INTO public.training_sections (
    id, module_id, section_code, title, description, content_markdown,
    content_html, section_order, estimated_duration_minutes,
    is_interactive, interactive_elements, is_required
) VALUES (
    '{section['id']}',
    '{module['id']}',
    '{section['section_code']}',
    '{section['title'].replace("'", "''")}',
    '{section['description'].replace("'", "''")}',
    '{section['content_markdown'].replace("'", "''")}',
    '{section['content_html'].replace("'", "''")}',
    {section['section_order']},
    {section['estimated_duration_minutes']},
    {str(section['is_interactive']).lower()},
    '{json.dumps(section['interactive_elements'])}',
    {str(section['is_required']).lower()}
);
""")
            
            # Insert assessments
            f.write("\n-- Insert training assessments\n")
            for module in modules:
                for assessment in module.get('assessments', []):
                    f.write(f"""
INSERT INTO public.training_assessments (
    id, module_id, assessment_code, title, description, assessment_type,
    passing_score, max_attempts, time_limit_minutes, questions,
    is_required, is_active
) VALUES (
    '{assessment['id']}',
    '{module['id']}',
    '{assessment['assessment_code']}',
    '{assessment['title'].replace("'", "''")}',
    '{assessment['description'].replace("'", "''")}',
    '{assessment['assessment_type']}',
    {assessment['passing_score']},
    {assessment['max_attempts']},
    {assessment['time_limit_minutes']},
    '{json.dumps(assessment['questions'])}',
    {str(assessment['is_required']).lower()},
    {str(assessment['is_active']).lower()}
);
""")
        
        logger.info(f"Generated SQL insert statements: {sql_file}")


def main():
    """Main function to run the training content converter."""
    converter = TrainingContentConverter()
    
    logger.info("Starting training content conversion...")
    converted_modules = converter.convert_all_training_files()
    
    logger.info(f"Successfully converted {len(converted_modules)} training modules:")
    for module in converted_modules:
        logger.info(f"  - {module['title']} ({len(module['sections'])} sections)")
    
    logger.info("Training content conversion completed!")


if __name__ == "__main__":
    main()
