import requests
import json
import os
from typing import Dict, Any, Optional
import logging
import google.generativeai as genai

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NVIDIAContentGenerator:
    """AI Content Generator with NVIDIA and Gemini API integration"""
    
    def __init__(self, api_key: str = None, api_url: str = None):
        self.nvidia_api_key = api_key or os.getenv('NVIDIA_API_KEY')
        self.nvidia_api_url = api_url or os.getenv('NVIDIA_API_URL', 'https://integrate.api.nvidia.com/v1/chat/completions')
        self.gemini_api_key = os.getenv('GEMINI_API_KEY')
        
        # Configure Gemini
        if self.gemini_api_key:
            genai.configure(api_key=self.gemini_api_key)
            self.gemini_model = genai.GenerativeModel('gemini-pro')
            logger.info("Gemini API configured successfully")
        else:
            self.gemini_model = None
            logger.warning("Gemini API key not found")
            
        if not self.nvidia_api_key and not self.gemini_api_key:
            logger.warning("No API keys found. Using fallback content generation.")

    def generate_learning_content(self, module_name: str, role: str, level: str, difficulty: int = 1) -> str:
        """Generate learning content for a specific module using Gemini or fallback"""
        
        try:
            # Try Gemini first (primary choice)
            if self.gemini_model:
                prompt = self._create_detailed_content_prompt(module_name, role, level, difficulty)
                response = self.gemini_model.generate_content(prompt)
                if response and response.text:
                    formatted_content = self._format_gemini_response(response.text)
                    if formatted_content and len(formatted_content) > 100:  # Basic validation
                        return formatted_content
            
            # Try NVIDIA API as backup
            if self.nvidia_api_key:
                prompt = self._create_detailed_content_prompt(module_name, role, level, difficulty)
                response = self._make_api_request(prompt)
                if response:
                    formatted_content = self._format_content_response(response)
                    if formatted_content and len(formatted_content) > 100:  # Basic validation
                        return formatted_content
            
            # Use built-in templates if APIs fail
            logger.info(f"Using built-in template for {module_name}")
            return self._generate_fallback_content(module_name, role, level, difficulty)
            
        except Exception as e:
            logger.error(f"Error generating content: {e}")
            return self._generate_fallback_content(module_name, role, level, difficulty)

    def _create_detailed_content_prompt(self, module_name: str, role: str, level: str, difficulty: int) -> str:
        """Create a detailed prompt for content generation"""
        role_specific_content = {
            'data_scientist': {
                'Python Refresher': """
                    Create comprehensive learning content covering:
                    1. Python basics (variables, data types, control structures)
                    2. Data structures (lists, dictionaries, sets)
                    3. Functions and object-oriented programming
                    4. File handling and data manipulation
                    5. NumPy and Pandas basics
                    6. Error handling and debugging
                    Include practical examples focused on data analysis scenarios.
                """,
                'Advanced Machine Learning': """
                    Cover these essential ML topics:
                    1. Supervised vs Unsupervised Learning
                    2. Model Selection and Evaluation
                    3. Feature Engineering
                    4. Cross-Validation
                    5. Hyperparameter Tuning
                    Include code examples using scikit-learn.
                """
            },
            'software_engineer': {
                'HTML5 Fundamentals': """
                    Cover modern HTML5 topics:
                    1. Semantic Elements
                    2. Forms and Validation
                    3. Media Elements
                    4. LocalStorage and SessionStorage
                    5. Web Components
                    Include practical examples of responsive layouts.
                """
            }
        }

        base_prompt = f"""
        Create detailed, well-structured learning content for: {module_name}
        Target Audience: {role.replace('_', ' ').title()} at {level} level
        Difficulty Level: {difficulty}/3

        Content Requirements:
        1. Start with clear learning objectives
        2. Provide thorough explanations of concepts
        3. Include multiple practical examples
        4. Add code snippets where relevant
        5. Include exercises and practice problems
        6. End with a summary and next steps

        Format the content in clean HTML with:
        - Proper section headings (h1, h2, h3)
        - Code blocks with syntax highlighting
        - Bullet points and numbered lists
        - Tables for comparative information
        - Clear visual hierarchy

        Additional Requirements:
        - Start with fundamentals if beginner level
        - Include intermediate concepts for level > 1
        - Add advanced topics for difficulty > 2
        - Focus on practical applications
        - Include best practices and common pitfalls
        - Add real-world examples
        """

        # Add role-specific content requirements if available
        if role in role_specific_content and module_name in role_specific_content[role]:
            base_prompt += "\nSpecific Module Requirements:\n" + role_specific_content[role][module_name]

        return base_prompt

    def _format_gemini_response(self, response_text: str) -> str:
        """Format Gemini API response to clean HTML with proper styling"""
        # Remove markdown formatting
        content = response_text.replace('**', '').replace('*', '')
        content = content.replace('===', '').replace('---', '')
        
        # Convert to proper HTML structure
        lines = content.split('\n')
        formatted_content = '''
        <div class="learning-content">
            <style>
                .learning-content { max-width: 800px; margin: 0 auto; padding: 20px; }
                .learning-content h1 { color: #2c3e50; font-size: 2em; margin-bottom: 1em; }
                .learning-content h2 { color: #34495e; font-size: 1.5em; margin: 1em 0; }
                .learning-content h3 { color: #7f8c8d; font-size: 1.2em; margin: 0.8em 0; }
                .learning-content p { line-height: 1.6; margin: 1em 0; }
                .learning-content pre { background: #f8f9fa; padding: 15px; border-radius: 5px; overflow-x: auto; }
                .learning-content code { font-family: 'Courier New', monospace; }
                .learning-content ul, .learning-content ol { margin: 1em 0; padding-left: 2em; }
                .learning-content li { margin: 0.5em 0; }
                .exercise-section { background: #f0f7ff; padding: 20px; border-radius: 5px; margin: 1em 0; }
            </style>
        '''
        
        in_code_block = False
        code_buffer = []
        current_list_type = None
        
        for line in lines:
            line = line.strip()
            if not line:
                if in_code_block:
                    code_buffer.append(line)
                else:
                    formatted_content += '<br>'
                continue
                
            # Handle code blocks
            if line.startswith('```'):
                if not in_code_block:
                    in_code_block = True
                    lang = line[3:].strip() or 'plaintext'
                    code_buffer = []
                else:
                    in_code_block = False
                    code = '\n'.join(code_buffer)
                    formatted_content += f'''
                        <pre><code class="language-{lang}">
                        {code}
                        </code></pre>
                    '''
                continue
                
            if in_code_block:
                code_buffer.append(line)
                continue
                
            # Handle headings
            if line.startswith('#'):
                if current_list_type:
                    formatted_content += f'</{current_list_type}>'
                    current_list_type = None
                level = line.count('#')
                text = line.replace('#', '').strip()
                class_name = 'main-heading' if level == 1 else 'sub-heading'
                formatted_content += f'<h{level} class="{class_name}">{text}</h{level}>'
                continue

            # Handle lists
            if line.startswith('-') or line.startswith('*') or line.startswith('•'):
                if current_list_type != 'ul':
                    if current_list_type:
                        formatted_content += f'</{current_list_type}>'
                    formatted_content += '<ul>'
                    current_list_type = 'ul'
                text = line[1:].strip()
                formatted_content += f'<li>{text}</li>'
                continue

            if line[0].isdigit() and '.' in line[:3]:
                if current_list_type != 'ol':
                    if current_list_type:
                        formatted_content += f'</{current_list_type}>'
                    formatted_content += '<ol>'
                    current_list_type = 'ol'
                text = line[line.find('.')+1:].strip()
                formatted_content += f'<li>{text}</li>'
                continue

            # Close any open lists
            if current_list_type and not (line.startswith('-') or line.startswith('*') or line.startswith('•') or (line[0].isdigit() and '.' in line[:3])):
                formatted_content += f'</{current_list_type}>'
                current_list_type = None

            # Handle paragraphs
            formatted_content += f'<p>{line}</p>'

        # Close any remaining open lists
        if current_list_type:
            formatted_content += f'</{current_list_type}>'

        formatted_content += '</div>'
        return formatted_content

    def _make_api_request(self, prompt: str) -> Optional[str]:
        """Make API request to NVIDIA"""
        
        if not self.nvidia_api_key:
            return None
            
        headers = {
            'Authorization': f'Bearer {self.nvidia_api_key}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            "model": "meta/llama-3.1-405b-instruct",
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.7,
            "max_tokens": 2048
        }
        
        try:
            response = requests.post(
                self.nvidia_api_url,
                headers=headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            return data['choices'][0]['message']['content']
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            return None
        except (KeyError, IndexError) as e:
            logger.error(f"Unexpected API response format: {e}")
            return None

    def generate_quiz_questions(self, module_name: str, role: str, difficulty: int = 1) -> list:
        """Generate quiz questions for a module"""
        
        try:
            # Try using Gemini for quiz generation if available
            if self.gemini_model:
                prompt = self._create_quiz_prompt(module_name, role, difficulty)
                response = self.gemini_model.generate_content(prompt)
                if response and response.text:
                    return self._parse_quiz_response(response.text)
            
            # Try NVIDIA API if Gemini fails or is not available
            if self.nvidia_api_key:
                prompt = self._create_quiz_prompt(module_name, role, difficulty)
                response = self._make_api_request(prompt)
                if response:
                    return self._parse_quiz_response(response)
            
            # If both APIs fail, use fallback
            return self._generate_fallback_quiz(module_name, role, difficulty)
                
        except Exception as e:
            logger.error(f"Error generating quiz: {e}")
            return self._generate_fallback_quiz(module_name, role, difficulty)

    def _create_quiz_prompt(self, module_name: str, role: str, difficulty: int) -> str:
        """Create a prompt for quiz generation"""
        
        difficulty_map = {1: "basic", 2: "intermediate", 3: "advanced"}
        difficulty_text = difficulty_map.get(difficulty, "intermediate")
        
        return f"""
        Create 5 multiple-choice quiz questions for a {role.replace('_', ' ')} student.
        
        Module: {module_name}
        Difficulty: {difficulty_text}
        
        For each question:
        - Make it practical and relevant to real-world scenarios
        - Include 4 answer options (A, B, C, D)
        - Mark the correct answer
        - Provide a brief explanation of why the answer is correct
        
        Format as JSON array:
        [
            {{
                "question": "Question text",
                "options": ["Option A", "Option B", "Option C", "Option D"],
                "correct": 0,
                "explanation": "Why this is correct"
            }}
        ]
        
        Focus on practical application and problem-solving rather than just theory.
        """

    def _parse_quiz_response(self, response: str) -> list:
        """Parse quiz response from API"""
        try:
            # Try to extract JSON from response
            start_idx = response.find('[')
            end_idx = response.rfind(']') + 1
            
            if start_idx != -1 and end_idx != -1:
                json_str = response[start_idx:end_idx]
                questions = json.loads(json_str)
                
                # Validate and clean up questions
                valid_questions = []
                for q in questions:
                    if all(key in q for key in ['question', 'options', 'correct', 'explanation']):
                        # Ensure correct answer index is valid
                        q['correct'] = max(0, min(len(q['options']) - 1, q['correct']))
                        valid_questions.append(q)
                
                return valid_questions[:5]  # Return up to 5 valid questions
            
            return self._generate_fallback_quiz('general', 'general', 1)
            
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse quiz response: {e}")
            return self._generate_fallback_quiz('general', 'general', 1)

    def _generate_fallback_quiz(self, module_name: str, role: str, difficulty: int) -> list:
        """Generate fallback quiz questions when APIs are unavailable"""
        
        # Basic template questions for different modules
        templates = {
            'python': [
                {
                    "question": "What is the correct way to create a variable in Python?",
                    "options": [
                        "x = 5",
                        "var x = 5",
                        "let x = 5",
                        "x := 5"
                    ],
                    "correct": 0,
                    "explanation": "In Python, variables are created by simply assigning a value using the = operator."
                },
                {
                    "question": "Which data structure is ordered, changeable, and allows duplicate values?",
                    "options": [
                        "List",
                        "Set",
                        "Dictionary",
                        "Tuple"
                    ],
                    "correct": 0,
                    "explanation": "Lists in Python are ordered, changeable, and allow duplicate values."
                }
            ],
            'html': [
                {
                    "question": "What does HTML stand for?",
                    "options": [
                        "HyperText Markup Language",
                        "High-Level Text Management Language",
                        "HyperTransfer Markup Language",
                        "HyperText Management Language"
                    ],
                    "correct": 0,
                    "explanation": "HTML stands for HyperText Markup Language, which is the standard markup language for creating web pages."
                },
                {
                    "question": "Which tag is used to define a paragraph in HTML?",
                    "options": ["<p>", "<par>", "<paragraph>", "<text>"],
                    "correct": 0,
                    "explanation": "The <p> tag is the standard way to define a paragraph in HTML."
                }
            ],
            'machine_learning': [
                {
                    "question": "What type of learning occurs when a model is trained on labeled data?",
                    "options": [
                        "Supervised Learning",
                        "Unsupervised Learning",
                        "Reinforcement Learning",
                        "Semi-supervised Learning"
                    ],
                    "correct": 0,
                    "explanation": "Supervised learning is when a model learns from labeled training data to make predictions."
                },
                {
                    "question": "Which metric is commonly used to evaluate regression models?",
                    "options": [
                        "Mean Squared Error",
                        "Accuracy",
                        "Precision",
                        "F1 Score"
                    ],
                    "correct": 0,
                    "explanation": "Mean Squared Error (MSE) is a common metric for evaluating regression models as it measures the average squared difference between predicted and actual values."
                }
            ]
        }
        
        # Get template questions for the module or use generic ones
        questions = templates.get(module_name.lower(), [
            {
                "question": f"What is the primary purpose of {module_name}?",
                "options": [
                    "To solve specific problems in computer science",
                    "To create web applications",
                    "To manage databases",
                    "To process data"
                ],
                "correct": 0,
                "explanation": f"The main purpose of {module_name} is to solve specific problems in computer science."
            },
            {
                "question": "Which best describes the role of documentation in programming?",
                "options": [
                    "To explain how code works and how to use it",
                    "To make files larger",
                    "To slow down program execution",
                    "To confuse other developers"
                ],
                "correct": 0,
                "explanation": "Documentation is crucial for explaining code functionality and usage to other developers."
            }
        ])
        
        return questions[:5]  # Return up to 5 questions

    def _generate_fallback_content(self, module_name: str, role: str, level: str, difficulty: int) -> str:
        """Generate fallback content when APIs are unavailable"""
        
        # Basic template content for different modules
        templates = {
            'python': """
                <div class="learning-content">
                    <style>
                        .learning-content { max-width: 800px; margin: 0 auto; padding: 20px; }
                        .learning-content h1 { color: #2c3e50; font-size: 2em; margin-bottom: 1em; }
                        .learning-content h2 { color: #34495e; font-size: 1.5em; margin: 1em 0; }
                        .learning-content p { line-height: 1.6; margin: 1em 0; }
                        .learning-content pre { background: #f8f9fa; padding: 15px; border-radius: 5px; overflow-x: auto; }
                        .learning-content code { font-family: 'Courier New', monospace; }
                        .learning-content ul { margin: 1em 0; padding-left: 2em; }
                    </style>
                    
                    <h1>Python Programming Fundamentals</h1>
                    
                    <h2>1. Variables and Data Types</h2>
                    <p>In Python, variables are created by assigning values using the = operator:</p>
                    <pre><code>
                    # Creating variables
                    name = "John"
                    age = 25
                    height = 1.75
                    is_student = True
                    </code></pre>
                    
                    <h2>2. Basic Operations</h2>
                    <p>Python supports various arithmetic operations:</p>
                    <pre><code>
                    # Arithmetic operations
                    x = 10
                    y = 3
                    
                    addition = x + y       # 13
                    subtraction = x - y    # 7
                    multiplication = x * y  # 30
                    division = x / y       # 3.333...
                    </code></pre>
                    
                    <h2>Practice Exercise</h2>
                    <p>Try creating a simple calculator program using the concepts learned:</p>
                    <pre><code>
                    def calculator(a, b, operation):
                        if operation == '+':
                            return a + b
                        elif operation == '-':
                            return a - b
                        elif operation == '*':
                            return a * b
                        elif operation == '/':
                            return a / b if b != 0 else "Error: Division by zero"
                    
                    # Test the calculator
                    print(calculator(10, 5, '+'))  # Output: 15
                    </code></pre>
                </div>
            """,
            'html': """
                <div class="learning-content">
                    <style>
                        .learning-content { max-width: 800px; margin: 0 auto; padding: 20px; }
                        .learning-content h1 { color: #2c3e50; font-size: 2em; margin-bottom: 1em; }
                        .learning-content h2 { color: #34495e; font-size: 1.5em; margin: 1em 0; }
                        .learning-content p { line-height: 1.6; margin: 1em 0; }
                        .learning-content pre { background: #f8f9fa; padding: 15px; border-radius: 5px; overflow-x: auto; }
                        .learning-content code { font-family: 'Courier New', monospace; }
                        .learning-content ul { margin: 1em 0; padding-left: 2em; }
                    </style>
                    
                    <h1>HTML Fundamentals</h1>
                    
                    <h2>1. Basic Structure</h2>
                    <p>Every HTML document needs a basic structure:</p>
                    <pre><code>
                    &lt;!DOCTYPE html&gt;
                    &lt;html&gt;
                        &lt;head&gt;
                            &lt;title&gt;My First Page&lt;/title&gt;
                        &lt;/head&gt;
                        &lt;body&gt;
                            &lt;h1&gt;Welcome to my website!&lt;/h1&gt;
                            &lt;p&gt;This is my first paragraph.&lt;/p&gt;
                        &lt;/body&gt;
                    &lt;/html&gt;
                    </code></pre>
                    
                    <h2>2. Common Elements</h2>
                    <ul>
                        <li>&lt;h1&gt; to &lt;h6&gt; - Headings</li>
                        <li>&lt;p&gt; - Paragraphs</li>
                        <li>&lt;a&gt; - Links</li>
                        <li>&lt;img&gt; - Images</li>
                        <li>&lt;ul&gt;, &lt;ol&gt;, &lt;li&gt; - Lists</li>
                    </ul>
                    
                    <h2>Practice Exercise</h2>
                    <p>Create a simple profile page using HTML elements:</p>
                    <pre><code>
                    &lt;!DOCTYPE html&gt;
                    &lt;html&gt;
                        &lt;head&gt;
                            &lt;title&gt;My Profile&lt;/title&gt;
                        &lt;/head&gt;
                        &lt;body&gt;
                            &lt;h1&gt;John Doe&lt;/h1&gt;
                            &lt;img src="profile.jpg" alt="Profile picture"&gt;
                            &lt;h2&gt;About Me&lt;/h2&gt;
                            &lt;p&gt;I am a web developer...&lt;/p&gt;
                            &lt;h2&gt;My Skills&lt;/h2&gt;
                            &lt;ul&gt;
                                &lt;li&gt;HTML&lt;/li&gt;
                                &lt;li&gt;CSS&lt;/li&gt;
                                &lt;li&gt;JavaScript&lt;/li&gt;
                            &lt;/ul&gt;
                        &lt;/body&gt;
                    &lt;/html&gt;
                    </code></pre>
                </div>
            """
        }
        
        # Get template content for the module or use a generic template
        content = templates.get(module_name.lower(), f"""
            <div class="learning-content">
                <style>
                    .learning-content {{ max-width: 800px; margin: 0 auto; padding: 20px; }}
                    .learning-content h1 {{ color: #2c3e50; font-size: 2em; margin-bottom: 1em; }}
                    .learning-content h2 {{ color: #34495e; font-size: 1.5em; margin: 1em 0; }}
                    .learning-content p {{ line-height: 1.6; margin: 1em 0; }}
                </style>
                
                <h1>Introduction to {module_name}</h1>
                
                <h2>Overview</h2>
                <p>This module introduces the fundamental concepts of {module_name}. You'll learn about the basic principles
                and practical applications in the field of computer science.</p>
                
                <h2>Learning Objectives</h2>
                <ul>
                    <li>Understand the core concepts of {module_name}</li>
                    <li>Learn about best practices and common patterns</li>
                    <li>Apply knowledge through practical exercises</li>
                    <li>Develop problem-solving skills in {module_name}</li>
                </ul>
                
                <h2>Key Concepts</h2>
                <p>We'll cover the following key concepts:</p>
                <ul>
                    <li>Fundamental principles and terminology</li>
                    <li>Common tools and techniques</li>
                    <li>Best practices and industry standards</li>
                    <li>Practical applications and case studies</li>
                </ul>
                
                <h2>Practice Exercise</h2>
                <p>Try solving these practice problems to reinforce your learning:</p>
                <ol>
                    <li>Identify the main components of a {module_name} system</li>
                    <li>Create a simple implementation using basic principles</li>
                    <li>Debug common issues and apply best practices</li>
                </ol>
                
                <h2>Next Steps</h2>
                <p>After completing this module, you'll be ready to:</p>
                <ul>
                    <li>Take on more advanced topics in {module_name}</li>
                    <li>Apply your knowledge to real-world projects</li>
                    <li>Explore related technologies and frameworks</li>
                </ul>
            </div>
        """)
        
        return content
