import json
import os
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging

from config.config import Config

logger = logging.getLogger(__name__)

class UserState:
    """User state management"""
    def __init__(self, user_id: int, username: str = None, first_name: str = None):
        self.user_id = user_id
        self.username = username
        self.first_name = first_name
        self.is_active = True
        self.created_at = datetime.now()
        self.last_activity = datetime.now()
        self.preferences = {
            'auto_signals': True,  # Receive automatic signals
            'manual_signals': True,  # Allow manual signals
            'notifications': True,   # Receive notifications
            'dashboard_auto_start': True  # Auto-start dashboard
        }
        self.stats = {
            'total_signals_received': 0,
            'manual_signals_requested': 0,
            'dashboard_sessions': 0,
            'last_command': None
        }
        
    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = datetime.now()
        self.is_active = True
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            'user_id': self.user_id,
            'username': self.username,
            'first_name': self.first_name,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat(),
            'last_activity': self.last_activity.isoformat(),
            'preferences': self.preferences,
            'stats': self.stats
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserState':
        """Create UserState from dictionary"""
        user_id = data['user_id']
        username = data.get('username')
        first_name = data.get('first_name')
        
        user_state = cls(user_id, username, first_name)
        user_state.is_active = data.get('is_active', True)
        user_state.created_at = datetime.fromisoformat(data['created_at'])
        user_state.last_activity = datetime.fromisoformat(data.get('last_activity', data['created_at']))
        user_state.preferences.update(data.get('preferences', {}))
        user_state.stats.update(data.get('stats', {}))
        
        return user_state

class UserManager:
    """User state and activity management"""
    
    def __init__(self):
        self.users: Dict[int, UserState] = {}
        self.data_file = os.path.join(Config.DATA_DIR, 'users.json')
        self.cleanup_interval = timedelta(hours=24)
        
        # Load existing users
        self._load_users()
        
        # Start cleanup task
        self._start_cleanup_task()
        
    def add_user(self, user_id: int, username: str = None, first_name: str = None) -> UserState:
        """Add or update user"""
        if user_id in self.users:
            # Update existing user
            user_state = self.users[user_id]
            user_state.username = username
            user_state.first_name = first_name
            user_state.update_activity()
        else:
            # Create new user
            user_state = UserState(user_id, username, first_name)
            self.users[user_id] = user_state
            logger.info(f"New user added: {user_id} (@{username or 'unknown'})")
            
        # Save to file
        self._save_users()
        
        return user_state
        
    def get_user(self, user_id: int) -> Optional[UserState]:
        """Get user state"""
        return self.users.get(user_id)
        
    def get_active_users(self) -> List[int]:
        """Get all active user IDs"""
        return [user_id for user_id, user_state in self.users.items() 
                if user_state.is_active]
                
    def update_user_activity(self, user_id: int, command: str = None):
        """Update user activity"""
        if user_id in self.users:
            user_state = self.users[user_id]
            user_state.update_activity()
            
            if command:
                user_state.stats['last_command'] = command
                
            self._save_users()
            
    def set_user_preference(self, user_id: int, key: str, value: Any):
        """Set user preference"""
        if user_id in self.users:
            user_state = self.users[user_id]
            user_state.preferences[key] = value
            user_state.update_activity()
            self._save_users()
            
    def get_user_preference(self, user_id: int, key: str, default: Any = None) -> Any:
        """Get user preference"""
        user_state = self.get_user(user_id)
        if user_state:
            return user_state.preferences.get(key, default)
        return default
        
    def increment_stat(self, user_id: int, stat_name: str):
        """Increment user statistic"""
        if user_id in self.users:
            user_state = self.users[user_id]
            user_state.stats[stat_name] = user_state.stats.get(stat_name, 0) + 1
            user_state.update_activity()
            self._save_users()
            
    def deactivate_user(self, user_id: int):
        """Deactivate user"""
        if user_id in self.users:
            self.users[user_id].is_active = False
            self._save_users()
            
    def get_user_statistics(self, user_id: int) -> Dict[str, Any]:
        """Get user statistics"""
        user_state = self.get_user(user_id)
        if not user_state:
            return {}
            
        return {
            'user_id': user_id,
            'username': user_state.username,
            'first_name': user_state.first_name,
            'is_active': user_state.is_active,
            'account_age_days': (datetime.now() - user_state.created_at).days,
            'last_activity': user_state.last_activity.strftime('%Y-%m-%d %H:%M:%S'),
            'preferences': user_state.preferences,
            'stats': user_state.stats
        }
        
    def get_all_users_statistics(self) -> Dict[str, Any]:
        """Get statistics for all users"""
        total_users = len(self.users)
        active_users = len(self.get_active_users())
        
        # Calculate average stats
        avg_signals_received = sum(user.stats['total_signals_received'] for user in self.users.values()) / total_users if total_users > 0 else 0
        avg_manual_requests = sum(user.stats['manual_signals_requested'] for user in self.users.values()) / total_users if total_users > 0 else 0
        
        return {
            'total_users': total_users,
            'active_users': active_users,
            'inactive_users': total_users - active_users,
            'avg_signals_received': avg_signals_received,
            'avg_manual_requests': avg_manual_requests
        }
        
    def _start_cleanup_task(self):
        """Start periodic cleanup task"""
        asyncio.create_task(self._cleanup_loop())
        
    async def _cleanup_loop(self):
        """Periodically cleanup inactive users"""
        while True:
            try:
                await asyncio.sleep(3600)  # Run every hour
                self._cleanup_inactive_users()
                
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                
    def _cleanup_inactive_users(self):
        """Mark inactive users"""
        now = datetime.now()
        inactive_count = 0
        
        for user_id, user_state in list(self.users.items()):
            # Mark as inactive if no activity for 7 days
            if now - user_state.last_activity > timedelta(days=7):
                if user_state.is_active:
                    user_state.is_active = False
                    inactive_count += 1
                    
        if inactive_count > 0:
            self._save_users()
            logger.info(f"Marked {inactive_count} users as inactive")
            
    def _save_users(self):
        """Save users to file — Bug #5 fix: atomic write via temp+rename"""
        try:
            data = {
                'users': [user.to_dict() for user in self.users.values()],
                'last_save': datetime.now().isoformat()
            }
            tmp_path = self.data_file + '.tmp'
            with open(tmp_path, 'w') as f:
                json.dump(data, f, indent=2)
            os.replace(tmp_path, self.data_file)
                
        except Exception as e:
            logger.error(f"Error saving users: {e}")
            
    def _load_users(self):
        """Load users from file"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
                    
                for user_data in data.get('users', []):
                    user_state = UserState.from_dict(user_data)
                    self.users[user_state.user_id] = user_state
                    
                logger.info(f"Loaded {len(self.users)} users from file")
                
        except Exception as e:
            logger.error(f"Error loading users: {e}")
            
    def reset_user_data(self, user_id: int):
        """Reset all user data"""
        if user_id in self.users:
            # Keep basic info but reset stats and preferences
            user_state = self.users[user_id]
            user_state.stats = {
                'total_signals_received': 0,
                'manual_signals_requested': 0,
                'dashboard_sessions': 0,
                'last_command': None
            }
            user_state.preferences = {
                'auto_signals': True,
                'manual_signals': True,
                'notifications': True,
                'dashboard_auto_start': True
            }
            user_state.update_activity()
            self._save_users()
            
            logger.info(f"Reset data for user {user_id}")
            
    def export_user_data(self, user_id: int) -> Dict[str, Any]:
        """Export user data for GDPR compliance"""
        user_state = self.get_user(user_id)
        if not user_state:
            return {}
            
        return {
            'user_info': {
                'user_id': user_state.user_id,
                'username': user_state.username,
                'first_name': user_state.first_name,
                'created_at': user_state.created_at.isoformat(),
                'last_activity': user_state.last_activity.isoformat()
            },
            'preferences': user_state.preferences,
            'statistics': user_state.stats
        }
        
    def delete_user_data(self, user_id: int):
        """Delete all user data (GDPR)"""
        if user_id in self.users:
            del self.users[user_id]
            self._save_users()
            logger.info(f"Deleted all data for user {user_id}")
            
    def is_user_allowed_manual_signal(self, user_id: int) -> bool:
        """Check if user is allowed to request manual signal"""
        user_state = self.get_user(user_id)
        if not user_state:
            return False
            
        # Check rate limiting (max 1 request per minute)
        last_request = user_state.stats.get('last_manual_request_time')
        if last_request:
            last_time = datetime.fromisoformat(last_request)
            if datetime.now() - last_time < timedelta(minutes=1):
                return False
                
        return user_state.preferences.get('manual_signals', True)
        
    def record_manual_request(self, user_id: int):
        """Record manual signal request"""
        if user_id in self.users:
            user_state = self.users[user_id]
            user_state.stats['manual_signals_requested'] += 1
            user_state.stats['last_manual_request_time'] = datetime.now().isoformat()
            user_state.update_activity()
            self._save_users()