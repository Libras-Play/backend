"""
Gamification logic for user-service

Implements:
- XP and leveling system
- Streak tracking
- Achievement unlocking
- Event notifications
"""
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import logging

from app.config import get_settings
from app.aws_client import aws_client

settings = get_settings()
logger = logging.getLogger(__name__)


# ============= XP AND LEVELING =============

def add_xp(user: Dict[str, Any], xp: int) -> Tuple[Dict[str, Any], bool]:
    """
    Add XP to user and check for level up
    
    Args:
        user: User data dict
        xp: Amount of XP to add
        
    Returns:
        Tuple of (updated_user, level_up_occurred)
    """
    current_xp = user.get('xp', 0)
    current_level = user.get('level', 1)
    
    new_xp = current_xp + xp
    new_level = calculate_level(new_xp)
    
    level_up = new_level > current_level
    
    user['xp'] = new_xp
    user['level'] = new_level
    
    logger.info(f"User {user['userId']} gained {xp} XP. Total: {new_xp}, Level: {new_level}")
    
    return user, level_up


def calculate_level(xp: int) -> int:
    """
    Calculate level based on total XP
    
    Formula: level = 1 + (xp // XP_PER_LEVEL)
    
    Args:
        xp: Total XP
        
    Returns:
        Current level
    """
    if xp < 0:
        return 1
    
    return 1 + (xp // settings.XP_PER_LEVEL)


def xp_for_level(level: int) -> int:
    """
    Calculate total XP required to reach a level
    
    Args:
        level: Target level
        
    Returns:
        Total XP required
    """
    if level <= 1:
        return 0
    
    return (level - 1) * settings.XP_PER_LEVEL


def xp_progress_in_level(xp: int) -> Dict[str, int]:
    """
    Calculate progress within current level
    
    Args:
        xp: Total XP
        
    Returns:
        Dict with current_level, xp_in_level, xp_needed_for_next
    """
    current_level = calculate_level(xp)
    xp_for_current = xp_for_level(current_level)
    xp_in_level = xp - xp_for_current
    xp_needed = settings.XP_PER_LEVEL - xp_in_level
    
    return {
        'currentLevel': current_level,
        'xpInLevel': xp_in_level,
        'xpNeededForNext': xp_needed,
        'xpPerLevel': settings.XP_PER_LEVEL,
    }


# ============= STREAK TRACKING =============

def update_streak(user: Dict[str, Any], activity_date: Optional[datetime] = None) -> Dict[str, Any]:
    """
    Update user's streak based on activity
    
    Streak logic:
    - If activity within STREAK_HOURS_THRESHOLD: increment or maintain
    - If gap > threshold: reset to 1
    
    Args:
        user: User data dict
        activity_date: Date of activity (defaults to now)
        
    Returns:
        Updated user dict with new streak data
    """
    if activity_date is None:
        activity_date = datetime.utcnow()
    
    current_streak = user.get('streakDays', 0)
    last_streak_date_str = user.get('lastStreakDate')
    
    # First activity ever
    if not last_streak_date_str:
        user['streakDays'] = 1
        user['lastStreakDate'] = activity_date.isoformat()
        logger.info(f"User {user['userId']} started streak: 1 day")
        return user
    
    last_streak_date = datetime.fromisoformat(last_streak_date_str)
    
    # Calculate hours since last activity
    hours_diff = (activity_date - last_streak_date).total_seconds() / 3600
    
    # Activity on same day (within a few hours) - maintain streak
    if hours_diff < 6:
        # Maintain streak, update timestamp
        user['lastStreakDate'] = activity_date.isoformat()
        logger.debug(f"User {user['userId']} maintained streak: {current_streak} days (same day)")
    
    # Activity within valid streak window (next day, within threshold)
    elif hours_diff < settings.STREAK_HOURS_THRESHOLD:
        # Increment streak
        new_streak = current_streak + 1
        user['streakDays'] = new_streak
        user['lastStreakDate'] = activity_date.isoformat()
        logger.info(f"User {user['userId']} increased streak to {new_streak} days")
        
        # Check for milestone achievements
        check_streak_milestone(user, new_streak)
    
    # Streak broken
    else:
        logger.warning(f"User {user['userId']} broke streak of {current_streak} days")
        user['streakDays'] = 1
        user['lastStreakDate'] = activity_date.isoformat()
    
    return user


def check_streak_milestone(user: Dict[str, Any], streak_days: int):
    """
    Check if streak reached a milestone and notify
    
    Milestones: 7, 14, 30, 50, 100, 365 days
    
    Args:
        user: User data
        streak_days: Current streak
    """
    milestones = [7, 14, 30, 50, 100, 365]
    
    if streak_days in milestones:
        logger.info(f"User {user['userId']} reached {streak_days}-day streak milestone!")
        
        # Notify via SNS
        try:
            aws_client.notify_streak_milestone(user['userId'], streak_days)
        except Exception as e:
            logger.error(f"Failed to send streak milestone notification: {str(e)}")


# ============= ACHIEVEMENTS =============

# Achievement definitions
ACHIEVEMENTS = {
    'first_sign': {
        'code': 'first_sign',
        'title': 'Primeiro Sinal',
        'description': 'Complete seu primeiro exercício',
        'xp_reward': 10,
    },
    'perfect_score': {
        'code': 'perfect_score',
        'title': 'Perfeição',
        'description': 'Obtenha 100% em um exercício',
        'xp_reward': 25,
    },
    'week_warrior': {
        'code': 'week_warrior',
        'title': 'Guerreiro Semanal',
        'description': 'Mantenha uma sequência de 7 dias',
        'xp_reward': 50,
    },
    'month_master': {
        'code': 'month_master',
        'title': 'Mestre Mensal',
        'description': 'Mantenha uma sequência de 30 dias',
        'xp_reward': 200,
    },
    'level_5': {
        'code': 'level_5',
        'title': 'Intermediário',
        'description': 'Alcance o nível 5',
        'xp_reward': 50,
    },
    'level_10': {
        'code': 'level_10',
        'title': 'Avançado',
        'description': 'Alcance o nível 10',
        'xp_reward': 100,
    },
    'complete_level': {
        'code': 'complete_level',
        'title': 'Nível Completo',
        'description': 'Complete todos os exercícios de um nível',
        'xp_reward': 75,
    },
}


def check_achievements(
    user: Dict[str, Any],
    event_type: str,
    event_data: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Check and unlock achievements based on events
    
    Event types:
    - exercise_completed: First exercise, perfect score
    - level_up: Level milestones
    - streak_milestone: Streak achievements
    - level_completed: Complete all exercises in a level
    
    Args:
        user: User data
        event_type: Type of event
        event_data: Additional event data
        
    Returns:
        List of newly unlocked achievements
    """
    unlocked = []
    current_achievements = user.get('achievements', [])
    
    if event_type == 'exercise_completed':
        # First sign achievement
        if 'first_sign' not in current_achievements:
            unlocked.append(ACHIEVEMENTS['first_sign'])
            current_achievements.append('first_sign')
        
        # Perfect score achievement
        if event_data and event_data.get('score') == 100:
            if 'perfect_score' not in current_achievements:
                unlocked.append(ACHIEVEMENTS['perfect_score'])
                current_achievements.append('perfect_score')
    
    elif event_type == 'level_up':
        new_level = user.get('level', 1)
        
        # Level milestone achievements
        if new_level >= 5 and 'level_5' not in current_achievements:
            unlocked.append(ACHIEVEMENTS['level_5'])
            current_achievements.append('level_5')
        
        if new_level >= 10 and 'level_10' not in current_achievements:
            unlocked.append(ACHIEVEMENTS['level_10'])
            current_achievements.append('level_10')
    
    elif event_type == 'streak_milestone':
        streak_days = user.get('streakDays', 0)
        
        if streak_days >= 7 and 'week_warrior' not in current_achievements:
            unlocked.append(ACHIEVEMENTS['week_warrior'])
            current_achievements.append('week_warrior')
        
        if streak_days >= 30 and 'month_master' not in current_achievements:
            unlocked.append(ACHIEVEMENTS['month_master'])
            current_achievements.append('month_master')
    
    elif event_type == 'level_completed':
        if 'complete_level' not in current_achievements:
            unlocked.append(ACHIEVEMENTS['complete_level'])
            current_achievements.append('complete_level')
    
    user['achievements'] = current_achievements
    
    # Notify and award XP for unlocked achievements
    for achievement in unlocked:
        logger.info(f"User {user['userId']} unlocked achievement: {achievement['code']}")
        
        # Add XP reward
        user['xp'] = user.get('xp', 0) + achievement['xp_reward']
        
        # Send notification (fire and forget, don't await)
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(aws_client.notify_achievement(user['userId'], achievement['code']))
        except Exception as e:
            logger.debug(f"Could not send achievement notification (likely in test mode): {str(e)}")
    
    return unlocked


def get_achievement_progress(user: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get user's achievement progress
    
    Args:
        user: User data
        
    Returns:
        Dict with unlocked count and progress details
    """
    unlocked = user.get('achievements', [])
    total = len(ACHIEVEMENTS)
    
    progress = {
        'unlocked': len(unlocked),
        'total': total,
        'percentage': int((len(unlocked) / total) * 100) if total > 0 else 0,
        'achievements': [],
    }
    
    for code, achievement in ACHIEVEMENTS.items():
        progress['achievements'].append({
            'code': code,
            'title': achievement['title'],
            'description': achievement['description'],
            'xpReward': achievement['xp_reward'],
            'unlocked': code in unlocked,
        })
    
    return progress


# ============= GAMIFICATION EVENTS =============

async def process_exercise_completion(
    user: Dict[str, Any],
    score: int,
    xp_earned: int
) -> Dict[str, Any]:
    """
    Process all gamification logic when user completes an exercise
    
    Args:
        user: User data
        score: Score achieved (0-100)
        xp_earned: XP earned from exercise
        
    Returns:
        Dict with updates and notifications
    """
    result = {
        'xpGained': xp_earned,
        'coinsEarned': 0,
        'levelUp': False,
        'newLevel': user.get('level', 1),
        'streakUpdated': False,
        'achievementsUnlocked': [],
    }
    
    # Add XP and check level up
    user, level_up = add_xp(user, xp_earned)
    result['levelUp'] = level_up
    result['newLevel'] = user['level']
    
    if level_up:
        logger.info(f"User {user['userId']} leveled up to {user['level']}!")
        try:
            aws_client.notify_level_up(user['userId'], user['level'])
        except Exception as e:
            logger.error(f"Failed to send level up notification: {str(e)}")
        
        # Award coins for leveling up (50 coins per level)
        coins_reward = 50 * user['level']
        user['coins'] = user.get('coins', 0) + coins_reward
        result['coinsEarned'] += coins_reward
        logger.info(f"User {user['userId']} earned {coins_reward} coins for reaching level {user['level']}")
    
    # Update streak
    user = update_streak(user)
    result['streakUpdated'] = True
    result['currentStreak'] = user.get('streakDays', 0)
    
    # Award coins for streaks (10 coins per day, bonus at milestones)
    streak_coins = 10
    streak_days = user.get('streakDays', 0)
    
    # Streak milestones give extra coins
    if streak_days == 7:
        streak_coins += 100  # 7-day bonus
    elif streak_days == 14:
        streak_coins += 250  # 14-day bonus
    elif streak_days == 30:
        streak_coins += 500  # 30-day bonus
    elif streak_days == 100:
        streak_coins += 1000  # 100-day bonus
    
    user['coins'] = user.get('coins', 0) + streak_coins
    result['coinsEarned'] += streak_coins
    
    # Award coins based on score
    # Perfect score: 50 coins, Good (80-99): 30 coins, Pass (60-79): 15 coins
    if score == 100:
        score_coins = 50
    elif score >= 80:
        score_coins = 30
    elif score >= 60:
        score_coins = 15
    else:
        score_coins = 5  # Consolation coins
    
    user['coins'] = user.get('coins', 0) + score_coins
    result['coinsEarned'] += score_coins
    
    # Check achievements
    achievements = check_achievements(user, 'exercise_completed', {'score': score})
    result['achievementsUnlocked'] = [a['code'] for a in achievements]
    
    if level_up:
        level_achievements = check_achievements(user, 'level_up')
        result['achievementsUnlocked'].extend([a['code'] for a in level_achievements])
    
    return result
