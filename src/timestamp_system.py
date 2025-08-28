#!/usr/bin/env python3
"""
Enhanced Timestamp System for hAIveMind Ticket Management
Provides comprehensive timestamp tracking and time intelligence
"""

import pytz
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import json

@dataclass
class TimestampInfo:
    """Comprehensive timestamp information"""
    utc_timestamp: str
    local_timestamp: str
    timezone: str
    epoch_time: float
    human_readable: str
    relative_time: str

@dataclass
class TimelineEvent:
    """Timeline event with rich timestamp data"""
    event_type: str
    timestamp: str
    actor: str
    description: str
    duration_since_last: Optional[str] = None
    metadata: Dict[str, Any] = None

class EnhancedTimestampSystem:
    """Enhanced timestamp management for ticket operations"""
    
    def __init__(self, default_timezone: str = 'UTC'):
        self.default_timezone = default_timezone
        self.common_timezones = [
            'UTC', 'US/Eastern', 'US/Central', 'US/Mountain', 'US/Pacific',
            'Europe/London', 'Europe/Berlin', 'Asia/Tokyo', 'Australia/Sydney'
        ]
    
    def get_current_timestamp_info(self, timezone: str = None) -> TimestampInfo:
        """Get comprehensive current timestamp information"""
        tz = timezone or self.default_timezone
        now = datetime.now(pytz.timezone(tz))
        utc_now = datetime.now(pytz.UTC)
        
        return TimestampInfo(
            utc_timestamp=utc_now.isoformat(),
            local_timestamp=now.isoformat(),
            timezone=tz,
            epoch_time=utc_now.timestamp(),
            human_readable=now.strftime('%Y-%m-%d %H:%M:%S %Z'),
            relative_time=self._get_relative_time(utc_now, utc_now)
        )
    
    def format_message_timestamp(self, timezone: str = None) -> str:
        """Format timestamp for message inclusion"""
        info = self.get_current_timestamp_info(timezone)
        return f"🕐 Generated: {info.human_readable}"
    
    def parse_iso_timestamp(self, iso_string: str) -> TimestampInfo:
        """Parse ISO timestamp into comprehensive info"""
        try:
            # Handle both with and without timezone
            if iso_string.endswith('Z'):
                dt = datetime.fromisoformat(iso_string.replace('Z', '+00:00'))
            else:
                dt = datetime.fromisoformat(iso_string)
            
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=pytz.UTC)
            
            now = datetime.now(pytz.UTC)
            
            return TimestampInfo(
                utc_timestamp=dt.astimezone(pytz.UTC).isoformat(),
                local_timestamp=dt.isoformat(),
                timezone=str(dt.tzinfo),
                epoch_time=dt.timestamp(),
                human_readable=dt.strftime('%Y-%m-%d %H:%M:%S %Z'),
                relative_time=self._get_relative_time(dt, now)
            )
        except Exception as e:
            # Fallback for invalid timestamps
            now = datetime.now(pytz.UTC)
            return TimestampInfo(
                utc_timestamp=now.isoformat(),
                local_timestamp=now.isoformat(),
                timezone='UTC',
                epoch_time=now.timestamp(),
                human_readable=now.strftime('%Y-%m-%d %H:%M:%S %Z'),
                relative_time='just now'
            )
    
    def calculate_duration(self, start_time: str, end_time: str = None) -> Dict[str, Any]:
        """Calculate duration between timestamps"""
        start_dt = self.parse_iso_timestamp(start_time)
        end_dt = self.parse_iso_timestamp(end_time) if end_time else self.get_current_timestamp_info()
        
        start = datetime.fromisoformat(start_dt.utc_timestamp.replace('Z', '+00:00'))
        end = datetime.fromisoformat(end_dt.utc_timestamp.replace('Z', '+00:00'))
        
        if start.tzinfo is None:
            start = start.replace(tzinfo=pytz.UTC)
        if end.tzinfo is None:
            end = end.replace(tzinfo=pytz.UTC)
        
        duration = end - start
        
        return {
            'total_seconds': duration.total_seconds(),
            'total_minutes': duration.total_seconds() / 60,
            'total_hours': duration.total_seconds() / 3600,
            'total_days': duration.days,
            'human_readable': self._format_duration(duration),
            'precise': str(duration)
        }
    
    def create_timeline_event(self, event_type: str, actor: str, 
                            description: str, metadata: Dict[str, Any] = None,
                            timezone: str = None) -> TimelineEvent:
        """Create a timeline event with timestamp"""
        timestamp_info = self.get_current_timestamp_info(timezone)
        
        return TimelineEvent(
            event_type=event_type,
            timestamp=timestamp_info.utc_timestamp,
            actor=actor,
            description=description,
            metadata=metadata or {}
        )
    
    def build_timeline(self, events: List[TimelineEvent]) -> List[TimelineEvent]:
        """Build timeline with duration calculations between events"""
        if not events:
            return []
        
        enhanced_events = []
        for i, event in enumerate(events):
            enhanced_event = event
            
            if i > 0:
                prev_time = events[i-1].timestamp
                duration_info = self.calculate_duration(prev_time, event.timestamp)
                enhanced_event.duration_since_last = duration_info['human_readable']
            
            enhanced_events.append(enhanced_event)
        
        return enhanced_events
    
    def get_ticket_age(self, created_at: str) -> Dict[str, Any]:
        """Calculate ticket age from creation time"""
        return self.calculate_duration(created_at)
    
    def get_time_in_status(self, status_changes: List[Dict[str, str]]) -> Dict[str, str]:
        """Calculate time spent in each status"""
        if not status_changes:
            return {}
        
        time_in_status = {}
        current_time = self.get_current_timestamp_info().utc_timestamp
        
        for i, change in enumerate(status_changes):
            status = change.get('status', 'unknown')
            start_time = change.get('timestamp')
            
            if i < len(status_changes) - 1:
                end_time = status_changes[i + 1].get('timestamp')
            else:
                end_time = current_time
            
            if start_time:
                duration_info = self.calculate_duration(start_time, end_time)
                time_in_status[status] = duration_info['human_readable']
        
        return time_in_status
    
    def format_ticket_timestamps(self, ticket_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format all timestamps in ticket data for display"""
        formatted = {}
        
        # Handle created_at
        if 'created_at' in ticket_data:
            created_info = self.parse_iso_timestamp(ticket_data['created_at'])
            formatted['created'] = {
                'absolute': created_info.human_readable,
                'relative': created_info.relative_time,
                'iso': created_info.utc_timestamp
            }
            
            # Calculate age
            age_info = self.get_ticket_age(ticket_data['created_at'])
            formatted['age'] = age_info['human_readable']
        
        # Handle updated_at
        if 'updated_at' in ticket_data:
            updated_info = self.parse_iso_timestamp(ticket_data['updated_at'])
            formatted['last_updated'] = {
                'absolute': updated_info.human_readable,
                'relative': updated_info.relative_time,
                'iso': updated_info.utc_timestamp
            }
        
        # Handle due_date if present
        if ticket_data.get('metadata', {}).get('due_date'):
            due_date = ticket_data['metadata']['due_date']
            due_info = self.parse_iso_timestamp(due_date)
            now = datetime.now(pytz.UTC)
            due_dt = datetime.fromisoformat(due_info.utc_timestamp.replace('Z', '+00:00'))
            
            is_overdue = due_dt < now
            time_until_due = self.calculate_duration(now.isoformat(), due_date)
            
            formatted['due_date'] = {
                'absolute': due_info.human_readable,
                'relative': due_info.relative_time,
                'is_overdue': is_overdue,
                'time_remaining': time_until_due['human_readable'] if not is_overdue else None,
                'overdue_by': time_until_due['human_readable'] if is_overdue else None
            }
        
        return formatted
    
    def _get_relative_time(self, target_time: datetime, reference_time: datetime) -> str:
        """Get human-readable relative time"""
        if target_time.tzinfo is None:
            target_time = target_time.replace(tzinfo=pytz.UTC)
        if reference_time.tzinfo is None:
            reference_time = reference_time.replace(tzinfo=pytz.UTC)
        
        diff = reference_time - target_time
        
        if diff.total_seconds() < 60:
            return "just now"
        elif diff.total_seconds() < 3600:
            minutes = int(diff.total_seconds() / 60)
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        elif diff.total_seconds() < 86400:
            hours = int(diff.total_seconds() / 3600)
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif diff.days < 30:
            return f"{diff.days} day{'s' if diff.days != 1 else ''} ago"
        elif diff.days < 365:
            months = int(diff.days / 30)
            return f"{months} month{'s' if months != 1 else ''} ago"
        else:
            years = int(diff.days / 365)
            return f"{years} year{'s' if years != 1 else ''} ago"
    
    def _format_duration(self, duration: timedelta) -> str:
        """Format duration in human-readable format"""
        total_seconds = int(duration.total_seconds())
        
        if total_seconds < 60:
            return f"{total_seconds}s"
        elif total_seconds < 3600:
            minutes = total_seconds // 60
            seconds = total_seconds % 60
            if seconds > 0:
                return f"{minutes}m {seconds}s"
            else:
                return f"{minutes}m"
        elif total_seconds < 86400:
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            if minutes > 0:
                return f"{hours}h {minutes}m"
            else:
                return f"{hours}h"
        else:
            days = duration.days
            hours = (total_seconds % 86400) // 3600
            if hours > 0:
                return f"{days}d {hours}h"
            else:
                return f"{days}d"
    
    def get_business_hours_duration(self, start_time: str, end_time: str = None,
                                  business_start: int = 9, business_end: int = 17,
                                  weekends_included: bool = False) -> Dict[str, Any]:
        """Calculate duration considering business hours"""
        start_dt = self.parse_iso_timestamp(start_time)
        end_dt = self.parse_iso_timestamp(end_time) if end_time else self.get_current_timestamp_info()
        
        start = datetime.fromisoformat(start_dt.utc_timestamp.replace('Z', '+00:00'))
        end = datetime.fromisoformat(end_dt.utc_timestamp.replace('Z', '+00:00'))
        
        business_hours = 0
        current = start.replace(hour=business_start, minute=0, second=0, microsecond=0)
        
        while current < end:
            # Skip weekends if not included
            if not weekends_included and current.weekday() >= 5:
                current += timedelta(days=1)
                continue
            
            # Calculate business hours for this day
            day_start = max(current.replace(hour=business_start), start)
            day_end = min(current.replace(hour=business_end), end)
            
            if day_end > day_start:
                business_hours += (day_end - day_start).total_seconds() / 3600
            
            current += timedelta(days=1)
        
        total_duration = self.calculate_duration(start_time, end_time)
        
        return {
            'business_hours': business_hours,
            'business_hours_formatted': f"{business_hours:.1f}h",
            'total_hours': total_duration['total_hours'],
            'business_vs_total_ratio': business_hours / total_duration['total_hours'] if total_duration['total_hours'] > 0 else 0
        }