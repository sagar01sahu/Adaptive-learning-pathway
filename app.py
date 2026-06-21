from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from datetime import datetime
import os
import json
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///adaptive_learning.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
bcrypt = Bcrypt(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
CORS(app)

# Import models after creating app
from models import db, User, LearningPath, Progress, Content, QuizResult
db.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Import AI components after models
from nvidia_api import NVIDIAContentGenerator
from reinforcement_learning import AdaptiveLearningEngine

# Initialize AI components after imports
nvidia_generator = NVIDIAContentGenerator()
rl_engine = AdaptiveLearningEngine(db)

# Routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        data = request.get_json()
        name = data.get('name')
        email = data.get('email')
        password = data.get('password')
        
        # Check if user already exists
        if User.query.filter_by(email=email).first():
            return jsonify({'error': 'Email already registered'}), 400
        
        # Create new user
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        user = User(name=name, email=email, password_hash=hashed_password)
        db.session.add(user)
        db.session.commit()
        
        login_user(user)
        return jsonify({'success': True, 'redirect': url_for('role_selection')})
    
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        user = User.query.filter_by(email=email).first()
        
        if user and bcrypt.check_password_hash(user.password_hash, password):
            login_user(user)
            if user.role:
                return jsonify({'success': True, 'redirect': url_for('dashboard')})
            else:
                return jsonify({'success': True, 'redirect': url_for('role_selection')})
        else:
            return jsonify({'error': 'Invalid email or password'}), 401
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/role-selection', methods=['GET', 'POST'])
@login_required
def role_selection():
    if request.method == 'POST':
        data = request.get_json()
        role = data.get('role')
        
        current_user.role = role
        db.session.commit()
        
        return jsonify({'success': True, 'redirect': url_for('initial_quiz')})
    
    return render_template('role_selection.html')

@app.route('/initial-quiz', methods=['GET', 'POST'])
@login_required
def initial_quiz():
    if request.method == 'POST':
        data = request.get_json()
        answers = data.get('answers')
        
        # Calculate score and determine level
        score = calculate_quiz_score(answers, current_user.role)
        level = determine_level(score)
        
        current_user.level = level
        current_user.current_progress = 1
        db.session.commit()
        
        # Initialize learning path
        initialize_learning_path(current_user.id, current_user.role, level)
        
        return jsonify({'success': True, 'level': level, 'redirect': url_for('dashboard')})
    
    # Get quiz questions based on role
    questions = get_initial_quiz_questions(current_user.role)
    return render_template('initial_quiz.html', questions=questions)

@app.route('/dashboard')
@login_required
def dashboard():
    # Get user's learning path and progress
    learning_path = LearningPath.query.filter_by(
        role=current_user.role, 
        level=current_user.level
    ).order_by(LearningPath.module_order).all()
    
    progress = Progress.query.filter_by(user_id=current_user.id).first()
    if not progress:
        progress = Progress(user_id=current_user.id, completed_modules=[], difficulty=1)
        db.session.add(progress)
        db.session.commit()
    
    return render_template('dashboard.html', 
                         learning_path=learning_path, 
                         progress=progress,
                         user=current_user)

@app.route('/module/<int:module_id>')
@login_required
def module_content(module_id):
    module = LearningPath.query.get_or_404(module_id)
    
    # Check if module is unlocked
    progress = Progress.query.filter_by(user_id=current_user.id).first()
    if module.module_order > current_user.current_progress:
        return redirect(url_for('dashboard'))
    
    # Generate or retrieve content
    content = get_or_generate_content(module_id, progress.difficulty if progress else 1, current_user.id)
    
    return render_template('module.html', module=module, content=content)

@app.route('/get-content', methods=['POST'])
@login_required
def get_content():
    data = request.get_json()
    module_id = data.get('module_id')
    
    module = LearningPath.query.get_or_404(module_id)
    progress = Progress.query.filter_by(user_id=current_user.id).first()
    
    content = get_or_generate_content(module_id, progress.difficulty if progress else 1)
    
    return jsonify({'content': content.generated_text})

@app.route('/submit-test', methods=['POST'])
@login_required
def submit_test():
    data = request.get_json()
    module_id = data.get('module_id')
    answers = data.get('answers')
    
    # Calculate test score
    score = calculate_test_score(answers, module_id)
    
    # Update progress and RL state
    progress = Progress.query.filter_by(user_id=current_user.id).first()
    rl_result = update_reinforcement_learning(progress, score, data.get('time_taken'))
    
    # Save quiz result
    quiz_result = QuizResult(
        user_id=current_user.id,
        module_id=module_id,
        score=score,
        timestamp=datetime.utcnow()
    )
    db.session.add(quiz_result)
    
    # Check if user passed (score >= 60%)
    if score >= 60:
        # Update completed modules
        if module_id not in progress.completed_modules:
            progress.completed_modules.append(module_id)
        
        # Unlock next module
        current_user.current_progress = max(current_user.current_progress, module_id + 1)
        
    db.session.commit()
    
    # Generate personalized hints
    hints = rl_engine.generate_personalized_hints(current_user.id, module.module_name, score)
    
    return jsonify({
        'score': score,
        'passed': score >= 60,
        'difficulty_adjusted': True,
        'rl_feedback': rl_result,
        'hints': hints
    })

@app.route('/progress')
@login_required
def get_progress():
    progress = Progress.query.filter_by(user_id=current_user.id).first()
    total_modules = LearningPath.query.filter_by(
        role=current_user.role, 
        level=current_user.level
    ).count()
    
    completion_percentage = (len(progress.completed_modules) / total_modules * 100) if progress else 0
    
    return jsonify({
        'completion_percentage': completion_percentage,
        'completed_modules': progress.completed_modules if progress else [],
        'current_difficulty': progress.difficulty if progress else 1
    })

# Helper functions
def calculate_quiz_score(answers, role):
    # Simplified scoring logic
    correct_answers = 0
    total_questions = len(answers)
    
    # This would be replaced with actual quiz logic
    for answer in answers:
        if answer.get('correct', False):
            correct_answers += 1
    
    return (correct_answers / total_questions) * 100

def determine_level(score):
    if score < 50:
        return 'beginner'
    elif score < 80:
        return 'intermediate'
    else:
        return 'pro'

def get_initial_quiz_questions(role):
    # Generate comprehensive role-specific initial assessment questions (20+ questions)
    questions = {
        'software_engineer': [
            # Basic Programming Concepts (1-5)
            {'id': 1, 'question': 'What does HTML stand for?', 'options': ['HyperText Markup Language', 'High Tech Modern Language', 'Home Tool Markup Language', 'Hyperlink and Text Markup Language'], 'correct': 0},
            {'id': 2, 'question': 'Which of these is a programming language?', 'options': ['HTML', 'CSS', 'Python', 'SQL'], 'correct': 2},
            {'id': 3, 'question': 'What is a variable in programming?', 'options': ['A fixed value', 'A container for storing data', 'A type of loop', 'A function'], 'correct': 1},
            {'id': 4, 'question': 'Which symbol is used for comments in Python?', 'options': ['//', '/*', '#', '<!--'], 'correct': 2},
            {'id': 5, 'question': 'What does CSS stand for?', 'options': ['Computer Style Sheets', 'Cascading Style Sheets', 'Creative Style System', 'Code Style Structure'], 'correct': 1},
            
            # Intermediate Concepts (6-10)
            {'id': 6, 'question': 'What is the purpose of a function?', 'options': ['To store data', 'To reuse code', 'To create variables', 'To end a program'], 'correct': 1},
            {'id': 7, 'question': 'Which data structure uses LIFO (Last In, First Out)?', 'options': ['Queue', 'Array', 'Stack', 'Tree'], 'correct': 2},
            {'id': 8, 'question': 'What is Git used for?', 'options': ['Database management', 'Version control', 'Web hosting', 'Image editing'], 'correct': 1},
            {'id': 9, 'question': 'What does API stand for?', 'options': ['Application Programming Interface', 'Advanced Programming Integration', 'Automated Program Interaction', 'Application Process Integration'], 'correct': 0},
            {'id': 10, 'question': 'Which HTTP method is used to retrieve data?', 'options': ['POST', 'PUT', 'GET', 'DELETE'], 'correct': 2},
            
            # Advanced Concepts (11-15)
            {'id': 11, 'question': 'What is the time complexity of binary search?', 'options': ['O(n)', 'O(log n)', 'O(n²)', 'O(1)'], 'correct': 1},
            {'id': 12, 'question': 'Which design pattern ensures only one instance of a class?', 'options': ['Factory', 'Observer', 'Singleton', 'Strategy'], 'correct': 2},
            {'id': 13, 'question': 'What is Docker used for?', 'options': ['Database queries', 'Containerization', 'Web design', 'Mobile development'], 'correct': 1},
            {'id': 14, 'question': 'Which database type is MongoDB?', 'options': ['Relational', 'NoSQL', 'Graph', 'Time-series'], 'correct': 1},
            {'id': 15, 'question': 'What does MVC stand for?', 'options': ['Model View Controller', 'Multiple View Components', 'Master View Control', 'Modern Visual Components'], 'correct': 0},
            
            # Expert Level (16-20)
            {'id': 16, 'question': 'What is microservices architecture?', 'options': ['Small web pages', 'Distributed system design', 'Tiny databases', 'Mobile app structure'], 'correct': 1},
            {'id': 17, 'question': 'Which tool is used for continuous integration?', 'options': ['Photoshop', 'Jenkins', 'Excel', 'PowerPoint'], 'correct': 1},
            {'id': 18, 'question': 'What is the purpose of load balancing?', 'options': ['Reduce server costs', 'Distribute traffic across servers', 'Increase storage', 'Improve UI design'], 'correct': 1},
            {'id': 19, 'question': 'Which protocol is used for secure web communication?', 'options': ['HTTP', 'FTP', 'HTTPS', 'SMTP'], 'correct': 2},
            {'id': 20, 'question': 'What is the main benefit of using TypeScript over JavaScript?', 'options': ['Faster execution', 'Type safety', 'Smaller file size', 'Better graphics'], 'correct': 1}
        ],
        'data_scientist': [
            # Basic Data Science (1-5)
            {'id': 1, 'question': 'What is the primary purpose of data visualization?', 'options': ['To make data look pretty', 'To communicate insights from data', 'To hide complex information', 'To replace statistical analysis'], 'correct': 1},
            {'id': 2, 'question': 'Which library is commonly used for data analysis in Python?', 'options': ['React', 'Pandas', 'Express', 'Laravel'], 'correct': 1},
            {'id': 3, 'question': 'What does CSV stand for?', 'options': ['Computer Separated Values', 'Comma Separated Values', 'Code System Values', 'Character String Variables'], 'correct': 1},
            {'id': 4, 'question': 'Which measure of central tendency is most affected by outliers?', 'options': ['Mean', 'Median', 'Mode', 'Range'], 'correct': 0},
            {'id': 5, 'question': 'What is the purpose of data cleaning?', 'options': ['To delete all data', 'To remove errors and inconsistencies', 'To make data smaller', 'To encrypt data'], 'correct': 1},
            
            # Statistics & Math (6-10)
            {'id': 6, 'question': 'What does correlation measure?', 'options': ['Causation between variables', 'Linear relationship strength', 'Data quality', 'Sample size'], 'correct': 1},
            {'id': 7, 'question': 'Which value represents perfect positive correlation?', 'options': ['0', '1', '-1', '0.5'], 'correct': 1},
            {'id': 8, 'question': 'What is a p-value used for?', 'options': ['Measuring correlation', 'Statistical significance testing', 'Data visualization', 'Feature selection'], 'correct': 1},
            {'id': 9, 'question': 'What is the normal distribution also called?', 'options': ['Uniform distribution', 'Bell curve', 'Linear distribution', 'Random distribution'], 'correct': 1},
            {'id': 10, 'question': 'What does standard deviation measure?', 'options': ['Central tendency', 'Data spread', 'Sample size', 'Correlation'], 'correct': 1},
            
            # Machine Learning Basics (11-15)
            {'id': 11, 'question': 'What type of learning uses labeled data?', 'options': ['Unsupervised', 'Supervised', 'Reinforcement', 'Semi-supervised'], 'correct': 1},
            {'id': 12, 'question': 'Which algorithm is used for classification?', 'options': ['K-means', 'Linear regression', 'Decision tree', 'PCA'], 'correct': 2},
            {'id': 13, 'question': 'What is overfitting?', 'options': ['Model performs well on training but poorly on new data', 'Model is too simple', 'Data is too clean', 'Algorithm is too fast'], 'correct': 0},
            {'id': 14, 'question': 'What is cross-validation used for?', 'options': ['Data cleaning', 'Model evaluation', 'Feature engineering', 'Data collection'], 'correct': 1},
            {'id': 15, 'question': 'Which metric is used for regression problems?', 'options': ['Accuracy', 'Precision', 'Mean Squared Error', 'F1-score'], 'correct': 2},
            
            # Advanced Topics (16-20)
            {'id': 16, 'question': 'What is feature engineering?', 'options': ['Building new features from existing data', 'Removing all features', 'Copying features', 'Renaming columns'], 'correct': 0},
            {'id': 17, 'question': 'Which technique reduces dimensionality?', 'options': ['Linear regression', 'PCA', 'K-means', 'Decision tree'], 'correct': 1},
            {'id': 18, 'question': 'What is ensemble learning?', 'options': ['Using one model', 'Combining multiple models', 'Data preprocessing', 'Feature selection'], 'correct': 1},
            {'id': 19, 'question': 'What is A/B testing used for?', 'options': ['Data cleaning', 'Comparing two versions', 'Model training', 'Database design'], 'correct': 1},
            {'id': 20, 'question': 'What does ROC curve measure?', 'options': ['Model accuracy over time', 'True positive vs false positive rates', 'Data quality', 'Feature importance'], 'correct': 1}
        ],
        'data_engineer': [
            # Database Basics (1-5)
            {'id': 1, 'question': 'What does ETL stand for?', 'options': ['Extract, Transform, Load', 'Execute, Test, Launch', 'Evaluate, Track, Learn', 'Export, Transfer, Link'], 'correct': 0},
            {'id': 2, 'question': 'Which tool is commonly used for big data processing?', 'options': ['Excel', 'Apache Spark', 'Photoshop', 'Word'], 'correct': 1},
            {'id': 3, 'question': 'What does SQL stand for?', 'options': ['Structured Query Language', 'Simple Query Logic', 'System Quality Language', 'Standard Question Language'], 'correct': 0},
            {'id': 4, 'question': 'Which command is used to retrieve data in SQL?', 'options': ['INSERT', 'UPDATE', 'SELECT', 'DELETE'], 'correct': 2},
            {'id': 5, 'question': 'What is a primary key?', 'options': ['A password', 'A unique identifier for records', 'A backup key', 'An encryption key'], 'correct': 1},
            
            # Data Processing (6-10)
            {'id': 6, 'question': 'What is data normalization?', 'options': ['Making data normal', 'Organizing data to reduce redundancy', 'Deleting data', 'Encrypting data'], 'correct': 1},
            {'id': 7, 'question': 'Which format is commonly used for data exchange?', 'options': ['PDF', 'JSON', 'DOC', 'EXE'], 'correct': 1},
            {'id': 8, 'question': 'What is a data warehouse?', 'options': ['A physical building', 'A centralized data repository', 'A backup system', 'A web server'], 'correct': 1},
            {'id': 9, 'question': 'What does ACID stand for in databases?', 'options': ['Atomicity, Consistency, Isolation, Durability', 'Advanced, Consistent, Integrated, Distributed', 'Automated, Controlled, Independent, Dynamic', 'Accurate, Complete, Indexed, Detailed'], 'correct': 0},
            {'id': 10, 'question': 'Which type of join returns all records from both tables?', 'options': ['INNER JOIN', 'LEFT JOIN', 'RIGHT JOIN', 'FULL OUTER JOIN'], 'correct': 3},
            
            # Big Data & Cloud (11-15)
            {'id': 11, 'question': 'What is Apache Kafka used for?', 'options': ['Web development', 'Stream processing', 'Image editing', 'Mobile apps'], 'correct': 1},
            {'id': 12, 'question': 'Which is a NoSQL database?', 'options': ['MySQL', 'PostgreSQL', 'MongoDB', 'SQLite'], 'correct': 2},
            {'id': 13, 'question': 'What is Hadoop used for?', 'options': ['Small data processing', 'Distributed storage and processing', 'Web hosting', 'Email services'], 'correct': 1},
            {'id': 14, 'question': 'What does API stand for?', 'options': ['Application Programming Interface', 'Advanced Programming Integration', 'Automated Program Interaction', 'Application Process Integration'], 'correct': 0},
            {'id': 15, 'question': 'Which cloud service provides data storage?', 'options': ['Amazon S3', 'Google Docs', 'Microsoft Word', 'Adobe Photoshop'], 'correct': 0},
            
            # Advanced Engineering (16-20)
            {'id': 16, 'question': 'What is data partitioning?', 'options': ['Deleting data', 'Dividing data into smaller chunks', 'Copying data', 'Encrypting data'], 'correct': 1},
            {'id': 17, 'question': 'What is Apache Airflow used for?', 'options': ['Data visualization', 'Workflow orchestration', 'Web development', 'Mobile apps'], 'correct': 1},
            {'id': 18, 'question': 'What is data lineage?', 'options': ['Data age', 'Data flow tracking', 'Data size', 'Data color'], 'correct': 1},
            {'id': 19, 'question': 'Which tool is used for real-time data processing?', 'options': ['Excel', 'Apache Storm', 'PowerPoint', 'Notepad'], 'correct': 1},
            {'id': 20, 'question': 'What is data governance?', 'options': ['Data politics', 'Managing data quality and compliance', 'Data storage', 'Data deletion'], 'correct': 1}
        ]
    }
    return questions.get(role, [])

def initialize_learning_path(user_id, role, level):
    # Load learning paths from JSON and create database entries
    learning_paths_data = get_learning_paths_data()
    
    if role in learning_paths_data['roles'] and level in learning_paths_data['roles'][role]:
        modules = learning_paths_data['roles'][role][level]
        
        for module_data in modules:
            existing_path = LearningPath.query.filter_by(
                role=role, 
                level=level, 
                module_order=module_data['order']
            ).first()
            
            if not existing_path:
                learning_path = LearningPath(
                    role=role,
                    level=level,
                    module_order=module_data['order'],
                    module_name=module_data['module']
                )
                db.session.add(learning_path)
        
        db.session.commit()

def get_learning_paths_data():
    return {
        "roles": {
            "software_engineer": {
                "beginner": [
                    {"order": 1, "module": "HTML Basics"},
                    {"order": 2, "module": "CSS Fundamentals"},
                    {"order": 3, "module": "JavaScript Basics"},
                    {"order": 4, "module": "Python Essentials"},
                    {"order": 5, "module": "Git & Version Control"},
                    {"order": 6, "module": "Mini Project: Build a Portfolio Website"}
                ],
                "intermediate": [
                    {"order": 1, "module": "ReactJS or Advanced JavaScript"},
                    {"order": 2, "module": "APIs & REST Services"},
                    {"order": 3, "module": "Database Basics (SQL & NoSQL)"},
                    {"order": 4, "module": "Backend with Python (Flask/FastAPI)"},
                    {"order": 5, "module": "Authentication & JWT"},
                    {"order": 6, "module": "Project: Full-Stack To-Do App"}
                ],
                "pro": [
                    {"order": 1, "module": "System Architecture & Design"},
                    {"order": 2, "module": "Cloud Deployment (AWS/GCP/Azure)"},
                    {"order": 3, "module": "Microservices & Containers (Docker)"},
                    {"order": 4, "module": "Security & Performance Optimization"},
                    {"order": 5, "module": "CI/CD Pipelines"},
                    {"order": 6, "module": "Capstone: Scalable Web App"}
                ]
            },
            "data_scientist": {
                "beginner": [
                    {"order": 1, "module": "Python Fundamentals for Data Science"},
                    {"order": 2, "module": "Introduction to Data Analysis"},
                    {"order": 3, "module": "Working with CSV and Excel Files"},
                    {"order": 4, "module": "Basic Statistics and Math"},
                    {"order": 5, "module": "Data Visualization Basics"},
                    {"order": 6, "module": "Project: Analyze a Simple Dataset"}
                ],
                "intermediate": [
                    {"order": 1, "module": "NumPy for Numerical Computing"},
                    {"order": 2, "module": "Pandas for Data Manipulation"},
                    {"order": 3, "module": "Advanced Data Visualization"},
                    {"order": 4, "module": "Statistics and Probability"},
                    {"order": 5, "module": "Introduction to Machine Learning"},
                    {"order": 6, "module": "Project: Build Your First ML Model"}
                ],
                "pro": [
                    {"order": 1, "module": "Advanced Machine Learning Algorithms"},
                    {"order": 2, "module": "Deep Learning Fundamentals"},
                    {"order": 3, "module": "Natural Language Processing"},
                    {"order": 4, "module": "Computer Vision Basics"},
                    {"order": 5, "module": "MLOps and Model Deployment"},
                    {"order": 6, "module": "Capstone: End-to-End ML Project"}
                ]
            },
            "artificial_intelligence": {
                "beginner": [
                    {"order": 1, "module": "Introduction to Artificial Intelligence"},
                    {"order": 2, "module": "Python Programming for AI"},
                    {"order": 3, "module": "Logic and Problem Solving"},
                    {"order": 4, "module": "Search Algorithms"},
                    {"order": 5, "module": "Basic Machine Learning Concepts"},
                    {"order": 6, "module": "Project: Simple AI Agent"}
                ],
                "intermediate": [
                    {"order": 1, "module": "Machine Learning Algorithms"},
                    {"order": 2, "module": "Neural Networks Fundamentals"},
                    {"order": 3, "module": "Natural Language Processing Basics"},
                    {"order": 4, "module": "Computer Vision Introduction"},
                    {"order": 5, "module": "Reinforcement Learning"},
                    {"order": 6, "module": "Project: Intelligent System"}
                ],
                "pro": [
                    {"order": 1, "module": "Advanced Deep Learning"},
                    {"order": 2, "module": "Generative AI and LLMs"},
                    {"order": 3, "module": "AI Ethics and Bias"},
                    {"order": 4, "module": "AI System Architecture"},
                    {"order": 5, "module": "Research and Innovation in AI"},
                    {"order": 6, "module": "Capstone: AI Research Project"}
                ]
            },
            "web_developer": {
                "beginner": [
                    {"order": 1, "module": "HTML5 Fundamentals"},
                    {"order": 2, "module": "CSS3 and Responsive Design"},
                    {"order": 3, "module": "JavaScript Basics"},
                    {"order": 4, "module": "DOM Manipulation"},
                    {"order": 5, "module": "Introduction to Web APIs"},
                    {"order": 6, "module": "Project: Interactive Website"}
                ],
                "intermediate": [
                    {"order": 1, "module": "Frontend Frameworks (React/Vue)"},
                    {"order": 2, "module": "Backend Development (Node.js)"},
                    {"order": 3, "module": "Database Integration"},
                    {"order": 4, "module": "RESTful APIs"},
                    {"order": 5, "module": "Authentication and Security"},
                    {"order": 6, "module": "Project: Full-Stack Web App"}
                ],
                "pro": [
                    {"order": 1, "module": "Advanced Frontend Architecture"},
                    {"order": 2, "module": "Microservices and APIs"},
                    {"order": 3, "module": "Performance Optimization"},
                    {"order": 4, "module": "DevOps for Web Development"},
                    {"order": 5, "module": "Progressive Web Apps"},
                    {"order": 6, "module": "Capstone: Enterprise Web Solution"}
                ]
            },
            "mobile_app_developer": {
                "beginner": [
                    {"order": 1, "module": "Mobile Development Fundamentals"},
                    {"order": 2, "module": "Introduction to React Native/Flutter"},
                    {"order": 3, "module": "UI/UX Design for Mobile"},
                    {"order": 4, "module": "Navigation and State Management"},
                    {"order": 5, "module": "Device APIs and Features"},
                    {"order": 6, "module": "Project: Simple Mobile App"}
                ],
                "intermediate": [
                    {"order": 1, "module": "Advanced Mobile UI Components"},
                    {"order": 2, "module": "Data Storage and Persistence"},
                    {"order": 3, "module": "Network Requests and APIs"},
                    {"order": 4, "module": "Push Notifications"},
                    {"order": 5, "module": "Testing Mobile Applications"},
                    {"order": 6, "module": "Project: Feature-Rich Mobile App"}
                ],
                "pro": [
                    {"order": 1, "module": "Native Development (iOS/Android)"},
                    {"order": 2, "module": "Mobile App Architecture Patterns"},
                    {"order": 3, "module": "Performance Optimization"},
                    {"order": 4, "module": "App Store Deployment"},
                    {"order": 5, "module": "Mobile Security Best Practices"},
                    {"order": 6, "module": "Capstone: Production Mobile App"}
                ]
            },
            "cybersecurity": {
                "beginner": [
                    {"order": 1, "module": "Introduction to Cybersecurity"},
                    {"order": 2, "module": "Network Security Fundamentals"},
                    {"order": 3, "module": "Cryptography Basics"},
                    {"order": 4, "module": "Common Security Threats"},
                    {"order": 5, "module": "Security Tools and Techniques"},
                    {"order": 6, "module": "Project: Security Assessment"}
                ],
                "intermediate": [
                    {"order": 1, "module": "Ethical Hacking and Penetration Testing"},
                    {"order": 2, "module": "Web Application Security"},
                    {"order": 3, "module": "Incident Response"},
                    {"order": 4, "module": "Security Frameworks and Compliance"},
                    {"order": 5, "module": "Digital Forensics"},
                    {"order": 6, "module": "Project: Security Audit"}
                ],
                "pro": [
                    {"order": 1, "module": "Advanced Threat Analysis"},
                    {"order": 2, "module": "Security Architecture Design"},
                    {"order": 3, "module": "Cloud Security"},
                    {"order": 4, "module": "IoT and Mobile Security"},
                    {"order": 5, "module": "Security Leadership and Management"},
                    {"order": 6, "module": "Capstone: Enterprise Security Strategy"}
                ]
            },
            "game_developer": {
                "beginner": [
                    {"order": 1, "module": "Introduction to Game Development"},
                    {"order": 2, "module": "Game Design Principles"},
                    {"order": 3, "module": "Programming with Unity/Unreal"},
                    {"order": 4, "module": "2D Game Development"},
                    {"order": 5, "module": "Game Physics and Mechanics"},
                    {"order": 6, "module": "Project: Simple 2D Game"}
                ],
                "intermediate": [
                    {"order": 1, "module": "3D Game Development"},
                    {"order": 2, "module": "Game AI and Behavior Trees"},
                    {"order": 3, "module": "Audio and Visual Effects"},
                    {"order": 4, "module": "Multiplayer Game Development"},
                    {"order": 5, "module": "Game Optimization"},
                    {"order": 6, "module": "Project: 3D Adventure Game"}
                ],
                "pro": [
                    {"order": 1, "module": "Advanced Game Engine Development"},
                    {"order": 2, "module": "VR/AR Game Development"},
                    {"order": 3, "module": "Game Analytics and Monetization"},
                    {"order": 4, "module": "Cross-Platform Development"},
                    {"order": 5, "module": "Game Publishing and Marketing"},
                    {"order": 6, "module": "Capstone: Commercial Game Project"}
                ]
            },
            "data_engineer": {
                "beginner": [
                    {"order": 1, "module": "Python for Data Pipelines"},
                    {"order": 2, "module": "SQL Fundamentals"},
                    {"order": 3, "module": "ETL Basics"},
                    {"order": 4, "module": "Intro to Data Warehousing"},
                    {"order": 5, "module": "Mini Project: Simple ETL Pipeline"}
                ],
                "intermediate": [
                    {"order": 1, "module": "Advanced SQL & Query Optimization"},
                    {"order": 2, "module": "Big Data Tools (Hadoop, Spark)"},
                    {"order": 3, "module": "Data Lakes vs Warehouses"},
                    {"order": 4, "module": "Stream Processing (Kafka, Flink)"},
                    {"order": 5, "module": "Project: Streaming Data Pipeline"}
                ],
                "pro": [
                    {"order": 1, "module": "Scalable Data Architectures"},
                    {"order": 2, "module": "Data Security & Governance"},
                    {"order": 3, "module": "Cloud Data Engineering (AWS Glue, GCP Dataflow)"},
                    {"order": 4, "module": "Real-time Analytics Systems"},
                    {"order": 5, "module": "Capstone: Enterprise Data Infrastructure"}
                ]
            }
        }
    }

def get_or_generate_content(module_id, difficulty, user_id=None):
    # Check if content already exists
    content = Content.query.filter_by(module_id=module_id, difficulty=difficulty).first()
    
    if not content:
        # Generate new content using NVIDIA API
        module = LearningPath.query.get(module_id)
        user = User.query.get(user_id) if user_id else current_user
        
        # Get content parameters from RL engine
        content_params = rl_engine.get_content_parameters(user.id, module.module_name) if user else {}
        
        generated_text = nvidia_generator.generate_learning_content(
            module_name=module.module_name,
            role=user.role if user else 'software_engineer',
            level=user.level if user else 'beginner',
            difficulty=difficulty
        )
        
        content = Content(
            module_id=module_id,
            generated_text=generated_text,
            difficulty=difficulty,
            timestamp=datetime.utcnow()
        )
        db.session.add(content)
        db.session.commit()
    
    return content

def generate_content_with_nvidia(module_name, difficulty):
    # Placeholder for NVIDIA API integration
    difficulty_text = {1: "beginner", 2: "intermediate", 3: "advanced"}
    
    prompt = f"Create comprehensive learning content for {module_name} at {difficulty_text.get(difficulty, 'intermediate')} level. Include explanations, examples, and practical exercises."
    
    # For now, return placeholder content
    # In production, this would make actual API calls to NVIDIA
    return f"""
    <h2>{module_name}</h2>
    <p>This is comprehensive {difficulty_text.get(difficulty, 'intermediate')}-level content for {module_name}.</p>
    <h3>Learning Objectives</h3>
    <ul>
        <li>Understand the core concepts of {module_name}</li>
        <li>Apply practical skills through hands-on examples</li>
        <li>Build confidence for real-world applications</li>
    </ul>
    <h3>Content Overview</h3>
    <p>Detailed explanation and examples would be generated here based on the difficulty level {difficulty}.</p>
    """

def calculate_test_score(answers, module_id):
    # Simplified test scoring
    correct_count = sum(1 for answer in answers if answer.get('correct', False))
    return (correct_count / len(answers)) * 100 if answers else 0

def update_reinforcement_learning(progress, score, time_taken=None):
    # Use RL engine for sophisticated difficulty adjustment
    rl_result = rl_engine.update_difficulty(
        user_id=progress.user_id,
        quiz_score=score,
        time_taken=time_taken
    )
    return rl_result

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
