import numpy as np
from typing import Dict, List, Tuple, Any
import json
from datetime import datetime, timedelta
from models import Progress, QuizResult, User
from flask_sqlalchemy import SQLAlchemy

class AdaptiveLearningEngine:
    """Reinforcement Learning engine for adaptive content difficulty"""
    
    def __init__(self, db: SQLAlchemy):
        self.db = db
        self.min_difficulty = 1
        self.max_difficulty = 3
        
        # RL parameters
        self.learning_rate = 0.1
        self.exploration_rate = 0.1
        self.decay_rate = 0.95
        
        # Performance thresholds
        self.poor_threshold = 60.0    # Below this = decrease difficulty
        self.good_threshold = 80.0    # Above this = increase difficulty
        self.excellent_threshold = 95.0
        
    def update_difficulty(self, user_id: int, quiz_score: float, time_taken: int = None) -> Dict[str, Any]:
        """Update user's difficulty based on performance using RL principles"""
        
        progress = Progress.query.filter_by(user_id=user_id).first()
        if not progress:
            return {"error": "Progress record not found"}
        
        old_difficulty = progress.difficulty
        
        # Get user's recent performance history
        performance_history = self._get_performance_history(user_id, limit=5)
        
        # Calculate performance metrics
        avg_score = np.mean([p['score'] for p in performance_history]) if performance_history else quiz_score
        score_trend = self._calculate_score_trend(performance_history)
        consistency = self._calculate_consistency(performance_history)
        
        # RL-based difficulty adjustment
        new_difficulty = self._calculate_new_difficulty(
            current_difficulty=old_difficulty,
            current_score=quiz_score,
            avg_score=avg_score,
            score_trend=score_trend,
            consistency=consistency,
            time_taken=time_taken
        )
        
        # Update progress record
        progress.difficulty = new_difficulty
        
        # Update RL state with additional metrics
        rl_state = progress.rl_state or {}
        rl_state.update({
            'last_update': datetime.utcnow().isoformat(),
            'score_history': [p['score'] for p in performance_history[-10:]],  # Keep last 10 scores
            'difficulty_changes': rl_state.get('difficulty_changes', 0) + (1 if new_difficulty != old_difficulty else 0),
            'avg_score': avg_score,
            'consistency_score': consistency,
            'exploration_count': rl_state.get('exploration_count', 0)
        })
        progress.rl_state = rl_state
        
        self.db.session.commit()
        
        return {
            'old_difficulty': old_difficulty,
            'new_difficulty': new_difficulty,
            'adjustment_reason': self._get_adjustment_reason(quiz_score, avg_score, score_trend),
            'performance_metrics': {
                'current_score': quiz_score,
                'average_score': avg_score,
                'score_trend': score_trend,
                'consistency': consistency
            }
        }
    
    def _calculate_new_difficulty(self, current_difficulty: int, current_score: float, 
                                avg_score: float, score_trend: float, consistency: float,
                                time_taken: int = None) -> int:
        """Calculate new difficulty using RL principles"""
        
        # Base adjustment based on current performance
        if current_score < self.poor_threshold:
            base_adjustment = -1
        elif current_score > self.good_threshold:
            base_adjustment = 1
        else:
            base_adjustment = 0
        
        # Trend-based adjustment
        trend_adjustment = 0
        if score_trend > 10:  # Strong positive trend
            trend_adjustment = 0.5
        elif score_trend < -10:  # Strong negative trend
            trend_adjustment = -0.5
        
        # Consistency-based adjustment
        consistency_adjustment = 0
        if consistency > 0.8 and avg_score > self.good_threshold:
            consistency_adjustment = 0.3  # Reward consistent high performance
        elif consistency < 0.5:
            consistency_adjustment = -0.2  # Penalize inconsistency
        
        # Time-based adjustment (if available)
        time_adjustment = 0
        if time_taken:
            # Assume optimal time is around 300 seconds (5 minutes)
            if time_taken < 120:  # Very fast completion
                time_adjustment = 0.2
            elif time_taken > 600:  # Very slow completion
                time_adjustment = -0.2
        
        # Combine all adjustments
        total_adjustment = base_adjustment + trend_adjustment + consistency_adjustment + time_adjustment
        
        # Apply exploration (occasionally try different difficulties)
        if np.random.random() < self.exploration_rate:
            exploration_adjustment = np.random.choice([-1, 0, 1])
            total_adjustment += exploration_adjustment * 0.5
        
        # Calculate new difficulty
        new_difficulty = current_difficulty + round(total_adjustment)
        
        # Ensure within bounds
        return max(self.min_difficulty, min(self.max_difficulty, new_difficulty))
    
    def _get_performance_history(self, user_id: int, limit: int = 10) -> List[Dict]:
        """Get recent quiz performance history"""
        
        recent_results = QuizResult.query.filter_by(user_id=user_id)\
            .order_by(QuizResult.timestamp.desc())\
            .limit(limit).all()
        
        return [
            {
                'score': result.score,
                'time_taken': result.time_taken,
                'timestamp': result.timestamp,
                'attempts': result.attempts
            }
            for result in recent_results
        ]
    
    def _calculate_score_trend(self, performance_history: List[Dict]) -> float:
        """Calculate the trend in scores (positive = improving, negative = declining)"""
        
        if len(performance_history) < 2:
            return 0.0
        
        scores = [p['score'] for p in performance_history]
        scores.reverse()  # Oldest first for trend calculation
        
        # Simple linear regression slope
        n = len(scores)
        x = np.arange(n)
        y = np.array(scores)
        
        slope = (n * np.sum(x * y) - np.sum(x) * np.sum(y)) / (n * np.sum(x**2) - (np.sum(x))**2)
        
        return slope
    
    def _calculate_consistency(self, performance_history: List[Dict]) -> float:
        """Calculate consistency score (0-1, where 1 is most consistent)"""
        
        if len(performance_history) < 2:
            return 1.0
        
        scores = [p['score'] for p in performance_history]
        std_dev = np.std(scores)
        mean_score = np.mean(scores)
        
        # Coefficient of variation (lower is more consistent)
        if mean_score > 0:
            cv = std_dev / mean_score
            # Convert to 0-1 scale where 1 is most consistent
            consistency = max(0, 1 - cv)
        else:
            consistency = 0
        
        return consistency
    
    def _get_adjustment_reason(self, current_score: float, avg_score: float, trend: float) -> str:
        """Get human-readable reason for difficulty adjustment"""
        
        if current_score < self.poor_threshold:
            return "Difficulty decreased due to low performance"
        elif current_score > self.excellent_threshold:
            return "Difficulty increased due to excellent performance"
        elif current_score > self.good_threshold and trend > 5:
            return "Difficulty increased due to consistent improvement"
        elif avg_score < self.poor_threshold:
            return "Difficulty decreased due to consistently low average"
        elif trend < -10:
            return "Difficulty decreased due to declining performance trend"
        else:
            return "Difficulty maintained based on current performance"
    
    def get_content_parameters(self, user_id: int, module_name: str) -> Dict[str, Any]:
        """Get parameters for content generation based on user's RL state"""
        
        progress = Progress.query.filter_by(user_id=user_id).first()
        user = User.query.get(user_id)
        
        if not progress or not user:
            return {"difficulty": 1, "style": "standard"}
        
        rl_state = progress.rl_state or {}
        performance_history = self._get_performance_history(user_id, limit=3)
        
        # Determine content style based on performance patterns
        avg_score = np.mean([p['score'] for p in performance_history]) if performance_history else 70
        
        if avg_score < 50:
            content_style = "remedial"  # Extra explanations, simpler examples
        elif avg_score > 85:
            content_style = "advanced"  # More challenging examples, less hand-holding
        else:
            content_style = "standard"
        
        # Determine focus areas based on weak points
        focus_areas = self._identify_focus_areas(user_id, user.role)
        
        return {
            "difficulty": progress.difficulty,
            "content_style": content_style,
            "focus_areas": focus_areas,
            "user_level": user.level,
            "user_role": user.role,
            "avg_performance": avg_score,
            "learning_velocity": self._calculate_learning_velocity(performance_history)
        }
    
    def _identify_focus_areas(self, user_id: int, role: str) -> List[str]:
        """Identify areas where user needs more focus based on performance"""
        
        # This would analyze quiz results by topic/module to identify weak areas
        # For now, return role-specific focus areas
        
        focus_map = {
            "software_engineer": ["debugging", "system_design", "algorithms"],
            "data_scientist": ["statistics", "model_evaluation", "data_preprocessing"],
            "data_engineer": ["data_pipelines", "sql_optimization", "distributed_systems"]
        }
        
        return focus_map.get(role, ["problem_solving", "best_practices"])
    
    def _calculate_learning_velocity(self, performance_history: List[Dict]) -> float:
        """Calculate how quickly the user is learning (improvement rate)"""
        
        if len(performance_history) < 2:
            return 0.0
        
        # Calculate improvement per unit time
        scores = [p['score'] for p in performance_history]
        timestamps = [p['timestamp'] for p in performance_history]
        
        if len(scores) >= 2:
            score_improvement = scores[0] - scores[-1]  # Most recent - oldest
            time_span = (timestamps[0] - timestamps[-1]).total_seconds() / 3600  # Hours
            
            if time_span > 0:
                return score_improvement / time_span
        
        return 0.0
    
    def generate_personalized_hints(self, user_id: int, module_name: str, 
                                  current_score: float) -> List[str]:
        """Generate personalized learning hints based on RL state"""
        
        progress = Progress.query.filter_by(user_id=user_id).first()
        if not progress:
            return []
        
        hints = []
        rl_state = progress.rl_state or {}
        
        # Performance-based hints
        if current_score < 60:
            hints.append("Take your time to understand the concepts before moving on")
            hints.append("Consider reviewing the material again before taking the quiz")
        elif current_score > 90:
            hints.append("Excellent work! You might be ready for more challenging content")
            hints.append("Try applying these concepts in a practical project")
        
        # Consistency-based hints
        consistency = rl_state.get('consistency_score', 0.5)
        if consistency < 0.5:
            hints.append("Try to maintain a consistent study schedule for better results")
        
        # Difficulty-based hints
        if progress.difficulty == 1:
            hints.append("Focus on building strong fundamentals")
        elif progress.difficulty == 3:
            hints.append("Challenge yourself with real-world applications")
        
        return hints[:3]  # Return top 3 hints
