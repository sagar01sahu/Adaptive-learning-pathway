#!/usr/bin/env python3
"""
Database initialization script for Adaptive Learning Platform
Run this script to create the database tables and populate initial data
"""

import os
import sys
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import User, LearningPath, Progress, Content, QuizResult, Badge

def create_tables():
    """Create all database tables"""
    print("Creating database tables...")
    with app.app_context():
        db.create_all()
        print("✓ Database tables created successfully")

def create_sample_user():
    """Create a sample demo user for testing"""
    print("Creating sample demo user...")
    with app.app_context():
        # Check if demo user already exists
        existing_user = User.query.filter_by(email='student@demo.com').first()
        if existing_user:
            print("✓ Demo user already exists")
            return existing_user
        
        # Create demo user
        demo_user = User(
            name='Demo Student',
            email='student@demo.com',
            password_hash=generate_password_hash('demo123'),
            role='software_engineer',
            level='beginner',
            current_progress=1
        )
        
        db.session.add(demo_user)
        db.session.commit()
        print("✓ Demo user created (email: student@demo.com, password: demo123)")
        return demo_user

def populate_learning_paths():
    """Populate learning paths for all roles and levels"""
    print("Populating learning paths...")
    
    learning_paths_data = {
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
                    {"order": 1, "module": "Python Refresher"},
                    {"order": 2, "module": "Numpy Basics"},
                    {"order": 3, "module": "Pandas & DataFrames"},
                    {"order": 4, "module": "Matplotlib & Seaborn Visualization"},
                    {"order": 5, "module": "Mini Project: Data Cleaning & Insights"}
                ],
                "intermediate": [
                    {"order": 1, "module": "Statistics & Probability for Data Science"},
                    {"order": 2, "module": "Scikit-learn ML Basics"},
                    {"order": 3, "module": "Feature Engineering"},
                    {"order": 4, "module": "Data Wrangling & Pipelines"},
                    {"order": 5, "module": "Project: Predictive Model"}
                ],
                "pro": [
                    {"order": 1, "module": "Deep Learning with TensorFlow/PyTorch"},
                    {"order": 2, "module": "NLP Applications"},
                    {"order": 3, "module": "Reinforcement Learning Basics"},
                    {"order": 4, "module": "Big Data Tools (Spark/Hadoop)"},
                    {"order": 5, "module": "MLOps & Deployment"},
                    {"order": 6, "module": "Capstone: AI-Powered Application"}
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
    
    with app.app_context():
        total_created = 0
        for role, levels in learning_paths_data['roles'].items():
            for level, modules in levels.items():
                for module_data in modules:
                    # Check if already exists
                    existing = LearningPath.query.filter_by(
                        role=role,
                        level=level,
                        module_order=module_data['order']
                    ).first()
                    
                    if not existing:
                        learning_path = LearningPath(
                            role=role,
                            level=level,
                            module_order=module_data['order'],
                            module_name=module_data['module'],
                            estimated_duration=45  # Default 45 minutes
                        )
                        db.session.add(learning_path)
                        total_created += 1
        
        db.session.commit()
        print(f"✓ Created {total_created} learning path modules")

def create_badges():
    """Create achievement badges"""
    print("Creating achievement badges...")
    
    badges_data = [
        {
            'name': 'First Steps',
            'description': 'Complete your first module',
            'icon': '🏆',
            'criteria': {'modules_completed': 1}
        },
        {
            'name': 'Streak Master',
            'description': 'Maintain a 7-day learning streak',
            'icon': '🔥',
            'criteria': {'streak_days': 7}
        },
        {
            'name': 'Perfect Score',
            'description': 'Score 100% on any quiz',
            'icon': '⭐',
            'criteria': {'perfect_score': True}
        },
        {
            'name': 'Fast Learner',
            'description': 'Complete 5 modules in one day',
            'icon': '⚡',
            'criteria': {'modules_per_day': 5}
        },
        {
            'name': 'Dedicated Student',
            'description': 'Complete 50% of your learning path',
            'icon': '📚',
            'criteria': {'completion_percentage': 50}
        }
    ]
    
    with app.app_context():
        created_count = 0
        for badge_data in badges_data:
            existing = Badge.query.filter_by(name=badge_data['name']).first()
            if not existing:
                badge = Badge(
                    name=badge_data['name'],
                    description=badge_data['description'],
                    icon=badge_data['icon'],
                    criteria=badge_data['criteria']
                )
                db.session.add(badge)
                created_count += 1
        
        db.session.commit()
        print(f"✓ Created {created_count} achievement badges")

def initialize_demo_progress():
    """Initialize progress for demo user"""
    print("Initializing demo user progress...")
    
    with app.app_context():
        demo_user = User.query.filter_by(email='student@demo.com').first()
        if not demo_user:
            print("❌ Demo user not found")
            return
        
        # Check if progress already exists
        existing_progress = Progress.query.filter_by(user_id=demo_user.id).first()
        if existing_progress:
            print("✓ Demo user progress already exists")
            return
        
        # Create initial progress
        progress = Progress(
            user_id=demo_user.id,
            completed_modules=[],
            difficulty=1,
            total_time_spent=0,
            streak_days=0
        )
        
        db.session.add(progress)
        db.session.commit()
        print("✓ Demo user progress initialized")

def main():
    """Main initialization function"""
    print("🚀 Initializing Adaptive Learning Platform Database...")
    print("=" * 50)
    
    try:
        # Create tables
        create_tables()
        
        # Populate data
        populate_learning_paths()
        create_badges()
        create_sample_user()
        initialize_demo_progress()
        
        print("=" * 50)
        print("✅ Database initialization completed successfully!")
        print("\n📋 Quick Start:")
        print("1. Set up your environment variables (copy .env.example to .env)")
        print("2. Install dependencies: pip install -r requirements.txt")
        print("3. Run the application: python app.py")
        print("4. Visit http://localhost:5000")
        print("5. Login with demo account: student@demo.com / demo123")
        
    except Exception as e:
        print(f"❌ Error during initialization: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
