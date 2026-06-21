from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
import json

# Initialize db - will be properly set in app.py
db = SQLAlchemy()

class User(UserMixin, db.Model):
    """User model for authentication and profile management"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(50))  # software_engineer, data_scientist, data_engineer
    level = db.Column(db.String(20))  # beginner, intermediate, pro
    current_progress = db.Column(db.Integer, default=1)  # Current unlocked module
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    progress = db.relationship('Progress', backref='user', uselist=False)
    quiz_results = db.relationship('QuizResult', backref='user', lazy=True)
    
    def __repr__(self):
        return f'<User {self.email}>'

class LearningPath(db.Model):
    """Learning path modules for different roles and levels"""
    __tablename__ = 'learning_paths'
    
    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.String(50), nullable=False)
    level = db.Column(db.String(20), nullable=False)
    module_order = db.Column(db.Integer, nullable=False)
    module_name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    estimated_duration = db.Column(db.Integer)  # in minutes
    
    # Relationships
    contents = db.relationship('Content', backref='module', lazy=True)
    quiz_results = db.relationship('QuizResult', backref='module', lazy=True)
    
    def __repr__(self):
        return f'<LearningPath {self.role}-{self.level}-{self.module_order}>'

class Progress(db.Model):
    """User progress tracking and RL state"""
    __tablename__ = 'progress'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    completed_modules = db.Column(db.JSON, default=list)  # List of completed module IDs
    difficulty = db.Column(db.Integer, default=1)  # RL difficulty level (1-3)
    total_time_spent = db.Column(db.Integer, default=0)  # in minutes
    streak_days = db.Column(db.Integer, default=0)
    last_activity = db.Column(db.DateTime, default=datetime.utcnow)
    rl_state = db.Column(db.JSON, default=dict)  # Additional RL parameters
    
    def __repr__(self):
        return f'<Progress User:{self.user_id} Difficulty:{self.difficulty}>'
    
    def get_completion_percentage(self):
        """Calculate completion percentage for user's current path"""
        if not self.user.role or not self.user.level:
            return 0
        
        total_modules = LearningPath.query.filter_by(
            role=self.user.role,
            level=self.user.level
        ).count()
        
        if total_modules == 0:
            return 0
        
        completed_count = len(self.completed_modules) if self.completed_modules else 0
        return (completed_count / total_modules) * 100

class Content(db.Model):
    """Generated learning content for modules"""
    __tablename__ = 'content'
    
    id = db.Column(db.Integer, primary_key=True)
    module_id = db.Column(db.Integer, db.ForeignKey('learning_paths.id'), nullable=False)
    generated_text = db.Column(db.Text, nullable=False)
    difficulty = db.Column(db.Integer, default=1)  # 1-3 difficulty level
    content_type = db.Column(db.String(50), default='lesson')  # lesson, exercise, project
    content_metadata = db.Column(db.JSON)  # Additional content metadata
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Content Module:{self.module_id} Difficulty:{self.difficulty}>'

class QuizResult(db.Model):
    """Quiz and test results for tracking performance"""
    __tablename__ = 'quiz_results'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    module_id = db.Column(db.Integer, db.ForeignKey('learning_paths.id'), nullable=False)
    score = db.Column(db.Float, nullable=False)  # Percentage score
    time_taken = db.Column(db.Integer)  # in seconds
    attempts = db.Column(db.Integer, default=1)
    answers = db.Column(db.JSON)  # Store user answers
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<QuizResult User:{self.user_id} Module:{self.module_id} Score:{self.score}>'
    
    def passed(self):
        """Check if user passed the quiz (>= 60%)"""
        return self.score >= 60.0

class Badge(db.Model):
    """Gamification badges for user achievements"""
    __tablename__ = 'badges'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    icon = db.Column(db.String(100))  # Icon class or image path
    criteria = db.Column(db.JSON)  # Badge earning criteria
    
    def __repr__(self):
        return f'<Badge {self.name}>'

class UserBadge(db.Model):
    """Association table for user badges"""
    __tablename__ = 'user_badges'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    badge_id = db.Column(db.Integer, db.ForeignKey('badges.id'), nullable=False)
    earned_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='user_badges')
    badge = db.relationship('Badge', backref='user_badges')
    
    def __repr__(self):
        return f'<UserBadge User:{self.user_id} Badge:{self.badge_id}>'
