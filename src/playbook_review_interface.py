#!/usr/bin/env python3
"""
Human Review Interface for Auto-Generated Playbooks

This module provides a comprehensive human review interface for auto-generated playbooks:
- Web-based review dashboard for pending suggestions
- Side-by-side comparison of generated vs existing playbooks
- Interactive editing and approval workflow
- Collaborative review with multiple reviewers
- Integration with version control for approved playbooks
- Feedback collection for continuous improvement
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Form, Depends
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Pydantic models for API
class ReviewRequest(BaseModel):
    suggestion_id: str
    action: str  # "approve", "reject", "needs_revision"
    reviewer_notes: Optional[str] = None
    modifications: Optional[Dict[str, Any]] = None

class FeedbackRequest(BaseModel):
    suggestion_id: str
    feedback_type: str  # "quality", "accuracy", "completeness", "usability"
    rating: int  # 1-5 scale
    comments: Optional[str] = None

@dataclass
class ReviewSession:
    """Represents a review session for a playbook suggestion"""
    session_id: str
    suggestion_id: str
    reviewer: str
    started_at: datetime
    status: str  # "in_progress", "completed", "abandoned"
    modifications: Dict[str, Any]
    comments: List[str]
    completed_at: Optional[datetime] = None

class PlaybookReviewInterface:
    """Human review interface for auto-generated playbooks"""
    
    def __init__(self, memory_storage, playbook_auto_gen_tools, version_control, config: Dict[str, Any]):
        self.memory_storage = memory_storage
        self.playbook_auto_gen_tools = playbook_auto_gen_tools
        self.version_control = version_control
        self.config = config
        
        # Review settings
        self.require_multiple_reviewers = config.get('require_multiple_reviewers', False)
        self.min_reviewers = config.get('min_reviewers', 1)
        self.auto_approve_threshold = config.get('auto_approve_threshold', 0.95)
        
        # Initialize FastAPI app
        self.app = FastAPI(title="Playbook Review Interface", version="1.0.0")
        self.templates = Jinja2Templates(directory="templates")
        
        # Active review sessions
        self.active_sessions = {}
        
        # Setup routes
        self._setup_routes()
        
        # Create templates directory if it doesn't exist
        self._create_templates()
    
    def _setup_routes(self):
        """Setup FastAPI routes for the review interface"""
        
        @self.app.get("/", response_class=HTMLResponse)
        async def dashboard(request: Request):
            """Main review dashboard"""
            try:
                # Get pending suggestions
                pending_result = await self.playbook_auto_gen_tools.get_pending_playbook_suggestions(limit=50)
                pending_suggestions = pending_result.get('suggestions', [])
                
                # Get review statistics
                stats = await self._get_review_statistics()
                
                return self.templates.TemplateResponse("dashboard.html", {
                    "request": request,
                    "pending_suggestions": pending_suggestions,
                    "stats": stats,
                    "title": "Playbook Review Dashboard"
                })
                
            except Exception as e:
                logger.error(f"Dashboard error: {e}")
                return HTMLResponse(f"<h1>Error loading dashboard: {e}</h1>", status_code=500)
        
        @self.app.get("/suggestion/{suggestion_id}", response_class=HTMLResponse)
        async def review_suggestion(request: Request, suggestion_id: str):
            """Detailed review page for a specific suggestion"""
            try:
                # Get the suggestion details
                suggestion = await self._get_suggestion_details(suggestion_id)
                if not suggestion:
                    raise HTTPException(status_code=404, detail="Suggestion not found")
                
                # Get similar existing playbooks for comparison
                similar_playbooks = await self._find_similar_playbooks(suggestion)
                
                # Get review history
                review_history = await self._get_review_history(suggestion_id)
                
                return self.templates.TemplateResponse("review_suggestion.html", {
                    "request": request,
                    "suggestion": suggestion,
                    "similar_playbooks": similar_playbooks,
                    "review_history": review_history,
                    "title": f"Review: {suggestion.get('title', 'Unknown')}"
                })
                
            except Exception as e:
                logger.error(f"Review suggestion error: {e}")
                return HTMLResponse(f"<h1>Error loading suggestion: {e}</h1>", status_code=500)
        
        @self.app.post("/api/review")
        async def submit_review(review: ReviewRequest):
            """Submit a review for a playbook suggestion"""
            try:
                # Validate review action
                if review.action not in ["approve", "reject", "needs_revision"]:
                    raise HTTPException(status_code=400, detail="Invalid review action")
                
                # Apply modifications if provided
                if review.modifications and review.action == "approve":
                    await self._apply_modifications(review.suggestion_id, review.modifications)
                
                # Submit the review
                result = await self.playbook_auto_gen_tools.review_playbook_suggestion(
                    suggestion_id=review.suggestion_id,
                    action=review.action,
                    reviewer_notes=review.reviewer_notes
                )
                
                # Record review in history
                await self._record_review_action(review)
                
                return JSONResponse(result)
                
            except Exception as e:
                logger.error(f"Review submission error: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/feedback")
        async def submit_feedback(feedback: FeedbackRequest):
            """Submit feedback on a playbook suggestion"""
            try:
                # Store feedback
                await self._store_feedback(feedback)
                
                return JSONResponse({"status": "success", "message": "Feedback recorded"})
                
            except Exception as e:
                logger.error(f"Feedback submission error: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/suggestion/{suggestion_id}/preview")
        async def preview_playbook(suggestion_id: str):
            """Get a preview of the generated playbook"""
            try:
                suggestion = await self._get_suggestion_details(suggestion_id)
                if not suggestion:
                    raise HTTPException(status_code=404, detail="Suggestion not found")
                
                playbook_spec = suggestion.get('playbook_spec', {})
                
                # Generate a readable preview
                preview = self._generate_playbook_preview(playbook_spec)
                
                return JSONResponse(preview)
                
            except Exception as e:
                logger.error(f"Preview generation error: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/stats")
        async def get_statistics():
            """Get review statistics"""
            try:
                stats = await self._get_review_statistics()
                return JSONResponse(stats)
            except Exception as e:
                logger.error(f"Statistics error: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/suggestions/pending")
        async def get_pending_suggestions(limit: int = 20):
            """Get pending suggestions via API"""
            try:
                result = await self.playbook_auto_gen_tools.get_pending_playbook_suggestions(limit=limit)
                return JSONResponse(result)
            except Exception as e:
                logger.error(f"Pending suggestions error: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/suggestion/{suggestion_id}/start_review")
        async def start_review_session(suggestion_id: str, reviewer: str = Form(...)):
            """Start a review session"""
            try:
                session = await self._start_review_session(suggestion_id, reviewer)
                return JSONResponse({"session_id": session.session_id, "status": "started"})
            except Exception as e:
                logger.error(f"Start review session error: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/compare/{suggestion_id}")
        async def compare_playbooks(request: Request, suggestion_id: str):
            """Compare generated playbook with existing ones"""
            try:
                suggestion = await self._get_suggestion_details(suggestion_id)
                if not suggestion:
                    raise HTTPException(status_code=404, detail="Suggestion not found")
                
                # Find similar playbooks
                similar_playbooks = await self._find_similar_playbooks(suggestion)
                
                # Generate comparison data
                comparisons = []
                for similar in similar_playbooks[:3]:  # Compare with top 3 similar
                    comparison = await self._generate_comparison(suggestion, similar)
                    comparisons.append(comparison)
                
                return self.templates.TemplateResponse("compare_playbooks.html", {
                    "request": request,
                    "suggestion": suggestion,
                    "comparisons": comparisons,
                    "title": f"Compare: {suggestion.get('title', 'Unknown')}"
                })
                
            except Exception as e:
                logger.error(f"Comparison error: {e}")
                return HTMLResponse(f"<h1>Error generating comparison: {e}</h1>", status_code=500)
    
    async def _get_suggestion_details(self, suggestion_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a suggestion"""
        try:
            search_results = await self.memory_storage.search_memories(
                query=f"suggestion_id:{suggestion_id}",
                category="playbook_suggestions",
                limit=1
            )
            
            if search_results.get('memories'):
                suggestion_data = json.loads(search_results['memories'][0].get('content', '{}'))
                return suggestion_data
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get suggestion details: {e}")
            return None
    
    async def _find_similar_playbooks(self, suggestion: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find existing playbooks similar to the suggestion"""
        try:
            # Extract key terms from the suggestion
            title = suggestion.get('title', '')
            description = suggestion.get('description', '')
            search_query = f"{title} {description}"
            
            # Search for similar runbooks
            search_results = await self.memory_storage.search_memories(
                query=search_query,
                category="runbooks",
                limit=10
            )
            
            similar_playbooks = []
            for memory in search_results.get('memories', []):
                playbook_info = {
                    'id': memory.get('id'),
                    'title': memory.get('metadata', {}).get('title', 'Unknown'),
                    'content': memory.get('content', ''),
                    'created_at': memory.get('timestamp'),
                    'similarity_score': memory.get('score', 0)
                }
                similar_playbooks.append(playbook_info)
            
            return similar_playbooks
            
        except Exception as e:
            logger.error(f"Failed to find similar playbooks: {e}")
            return []
    
    async def _get_review_history(self, suggestion_id: str) -> List[Dict[str, Any]]:
        """Get review history for a suggestion"""
        try:
            search_results = await self.memory_storage.search_memories(
                query=f"suggestion_id:{suggestion_id} review",
                category="review_history",
                limit=50
            )
            
            history = []
            for memory in search_results.get('memories', []):
                try:
                    review_data = json.loads(memory.get('content', '{}'))
                    history.append(review_data)
                except:
                    pass
            
            # Sort by timestamp
            history.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            return history
            
        except Exception as e:
            logger.error(f"Failed to get review history: {e}")
            return []
    
    async def _apply_modifications(self, suggestion_id: str, modifications: Dict[str, Any]):
        """Apply modifications to a suggestion before approval"""
        try:
            # Get the original suggestion
            suggestion = await self._get_suggestion_details(suggestion_id)
            if not suggestion:
                raise ValueError("Suggestion not found")
            
            # Apply modifications to the playbook spec
            original_spec = suggestion.get('playbook_spec', {})
            modified_spec = self._merge_modifications(original_spec, modifications)
            
            # Update the suggestion with modifications
            suggestion['playbook_spec'] = modified_spec
            suggestion['modified_at'] = datetime.now().isoformat()
            suggestion['has_modifications'] = True
            
            # Store the modified suggestion
            await self.memory_storage.store_memory(
                content=json.dumps(suggestion, default=str),
                category="playbook_suggestions",
                metadata={
                    **suggestion.get('metadata', {}),
                    "modified": True,
                    "modification_timestamp": datetime.now().isoformat()
                },
                tags=["modified", "playbook_suggestion"]
            )
            
            logger.info(f"Applied modifications to suggestion {suggestion_id}")
            
        except Exception as e:
            logger.error(f"Failed to apply modifications: {e}")
            raise
    
    def _merge_modifications(self, original: Dict[str, Any], modifications: Dict[str, Any]) -> Dict[str, Any]:
        """Merge modifications into the original playbook spec"""
        result = original.copy()
        
        # Simple recursive merge
        for key, value in modifications.items():
            if isinstance(value, dict) and key in result and isinstance(result[key], dict):
                result[key] = self._merge_modifications(result[key], value)
            else:
                result[key] = value
        
        return result
    
    async def _record_review_action(self, review: ReviewRequest):
        """Record a review action in the history"""
        try:
            review_record = {
                "suggestion_id": review.suggestion_id,
                "action": review.action,
                "reviewer_notes": review.reviewer_notes,
                "reviewer": "human_reviewer",  # Could be enhanced with actual user info
                "timestamp": datetime.now().isoformat(),
                "has_modifications": bool(review.modifications)
            }
            
            await self.memory_storage.store_memory(
                content=json.dumps(review_record),
                category="review_history",
                metadata={
                    "suggestion_id": review.suggestion_id,
                    "action": review.action,
                    "review_type": "human_review"
                },
                tags=["review", "human", review.action]
            )
            
        except Exception as e:
            logger.error(f"Failed to record review action: {e}")
    
    async def _store_feedback(self, feedback: FeedbackRequest):
        """Store feedback on a suggestion"""
        try:
            feedback_record = {
                "suggestion_id": feedback.suggestion_id,
                "feedback_type": feedback.feedback_type,
                "rating": feedback.rating,
                "comments": feedback.comments,
                "timestamp": datetime.now().isoformat()
            }
            
            await self.memory_storage.store_memory(
                content=json.dumps(feedback_record),
                category="review_feedback",
                metadata={
                    "suggestion_id": feedback.suggestion_id,
                    "feedback_type": feedback.feedback_type,
                    "rating": feedback.rating
                },
                tags=["feedback", "human", feedback.feedback_type]
            )
            
        except Exception as e:
            logger.error(f"Failed to store feedback: {e}")
            raise
    
    def _generate_playbook_preview(self, playbook_spec: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a readable preview of a playbook specification"""
        try:
            preview = {
                "name": playbook_spec.get('name', 'Unknown Playbook'),
                "description": playbook_spec.get('description', 'No description'),
                "category": playbook_spec.get('category', 'auto-generated'),
                "parameters": [],
                "steps": [],
                "estimated_duration": "Unknown"
            }
            
            # Process parameters
            for param in playbook_spec.get('parameters', []):
                preview["parameters"].append({
                    "name": param.get('name', 'Unknown'),
                    "required": param.get('required', False),
                    "description": param.get('description', 'No description')
                })
            
            # Process steps
            for i, step in enumerate(playbook_spec.get('steps', []), 1):
                step_preview = {
                    "number": i,
                    "id": step.get('id', f'step_{i}'),
                    "name": step.get('name', f'Step {i}'),
                    "action": step.get('action', 'unknown'),
                    "description": self._describe_step_action(step)
                }
                preview["steps"].append(step_preview)
            
            # Estimate duration
            step_count = len(preview["steps"])
            if step_count > 0:
                estimated_minutes = step_count * 2  # Rough estimate
                preview["estimated_duration"] = f"~{estimated_minutes} minutes"
            
            return preview
            
        except Exception as e:
            logger.error(f"Failed to generate preview: {e}")
            return {"error": str(e)}
    
    def _describe_step_action(self, step: Dict[str, Any]) -> str:
        """Generate a human-readable description of a step action"""
        action = step.get('action', 'unknown')
        args = step.get('args', {})
        
        if action == 'shell':
            command = args.get('command', 'unknown command')
            return f"Execute shell command: {command}"
        elif action == 'http_request':
            method = args.get('method', 'GET')
            url = args.get('url', 'unknown URL')
            return f"Make {method} request to {url}"
        elif action == 'wait':
            seconds = args.get('seconds', 1)
            return f"Wait for {seconds} seconds"
        elif action == 'noop':
            message = args.get('message', 'No operation')
            return f"Info: {message}"
        else:
            return f"Perform {action} action"
    
    async def _get_review_statistics(self) -> Dict[str, Any]:
        """Get comprehensive review statistics"""
        try:
            # Get all suggestions
            all_suggestions = await self.memory_storage.search_memories(
                query="suggestion_id",
                category="playbook_suggestions",
                limit=1000
            )
            
            total_suggestions = len(all_suggestions.get('memories', []))
            
            # Count by status
            status_counts = {"pending": 0, "approved": 0, "rejected": 0, "needs_revision": 0}
            confidence_scores = []
            
            for memory in all_suggestions.get('memories', []):
                try:
                    suggestion_data = json.loads(memory.get('content', '{}'))
                    status = suggestion_data.get('human_review_status', 'pending')
                    status_counts[status] = status_counts.get(status, 0) + 1
                    
                    confidence = suggestion_data.get('confidence_score', 0)
                    if confidence > 0:
                        confidence_scores.append(confidence)
                except:
                    pass
            
            # Calculate averages
            avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
            
            # Get review activity (last 7 days)
            recent_reviews = await self.memory_storage.search_memories(
                query="review human",
                category="review_history",
                limit=100
            )
            
            recent_count = 0
            for memory in recent_reviews.get('memories', []):
                try:
                    timestamp = datetime.fromisoformat(memory.get('timestamp', '').replace('Z', '+00:00'))
                    if timestamp >= datetime.now() - timedelta(days=7):
                        recent_count += 1
                except:
                    pass
            
            return {
                "total_suggestions": total_suggestions,
                "status_distribution": status_counts,
                "average_confidence_score": round(avg_confidence, 3),
                "recent_reviews_7_days": recent_count,
                "approval_rate": round(status_counts["approved"] / max(total_suggestions, 1), 3),
                "pending_count": status_counts["pending"],
                "high_confidence_pending": len([s for s in confidence_scores if s > 0.8])
            }
            
        except Exception as e:
            logger.error(f"Failed to get review statistics: {e}")
            return {}
    
    async def _start_review_session(self, suggestion_id: str, reviewer: str) -> ReviewSession:
        """Start a new review session"""
        try:
            session = ReviewSession(
                session_id=f"session_{suggestion_id}_{int(datetime.now().timestamp())}",
                suggestion_id=suggestion_id,
                reviewer=reviewer,
                started_at=datetime.now(),
                status="in_progress",
                modifications={},
                comments=[]
            )
            
            self.active_sessions[session.session_id] = session
            
            # Record session start
            await self.memory_storage.store_memory(
                content=json.dumps(asdict(session), default=str),
                category="review_sessions",
                metadata={
                    "session_id": session.session_id,
                    "suggestion_id": suggestion_id,
                    "reviewer": reviewer,
                    "status": "started"
                },
                tags=["review_session", "started"]
            )
            
            return session
            
        except Exception as e:
            logger.error(f"Failed to start review session: {e}")
            raise
    
    async def _generate_comparison(self, suggestion: Dict[str, Any], existing_playbook: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a detailed comparison between suggestion and existing playbook"""
        try:
            suggestion_spec = suggestion.get('playbook_spec', {})
            
            comparison = {
                "existing_playbook": {
                    "id": existing_playbook.get('id'),
                    "title": existing_playbook.get('title'),
                    "similarity_score": existing_playbook.get('similarity_score', 0)
                },
                "suggestion": {
                    "title": suggestion.get('title'),
                    "confidence_score": suggestion.get('confidence_score', 0)
                },
                "differences": {
                    "step_count": {
                        "suggestion": len(suggestion_spec.get('steps', [])),
                        "existing": len(existing_playbook.get('content', '').split('\n'))
                    },
                    "complexity": self._assess_complexity(suggestion_spec),
                    "automation_level": self._assess_automation_level(suggestion_spec)
                },
                "advantages": {
                    "suggestion": [],
                    "existing": []
                },
                "recommendation": "review_needed"
            }
            
            # Analyze advantages
            if suggestion.get('confidence_score', 0) > 0.8:
                comparison["advantages"]["suggestion"].append("High AI confidence score")
            
            if len(suggestion_spec.get('steps', [])) > 5:
                comparison["advantages"]["suggestion"].append("Comprehensive step coverage")
            
            if existing_playbook.get('similarity_score', 0) > 0.9:
                comparison["advantages"]["existing"].append("Very similar to current need")
            
            # Generate recommendation
            if suggestion.get('confidence_score', 0) > 0.9 and existing_playbook.get('similarity_score', 0) < 0.7:
                comparison["recommendation"] = "approve_suggestion"
            elif existing_playbook.get('similarity_score', 0) > 0.9:
                comparison["recommendation"] = "use_existing"
            
            return comparison
            
        except Exception as e:
            logger.error(f"Failed to generate comparison: {e}")
            return {"error": str(e)}
    
    def _assess_complexity(self, playbook_spec: Dict[str, Any]) -> str:
        """Assess the complexity level of a playbook"""
        step_count = len(playbook_spec.get('steps', []))
        param_count = len(playbook_spec.get('parameters', []))
        
        if step_count <= 3 and param_count <= 2:
            return "low"
        elif step_count <= 7 and param_count <= 5:
            return "medium"
        else:
            return "high"
    
    def _assess_automation_level(self, playbook_spec: Dict[str, Any]) -> str:
        """Assess the automation level of a playbook"""
        steps = playbook_spec.get('steps', [])
        automated_actions = ['shell', 'http_request', 'api_call']
        manual_actions = ['noop', 'wait']
        
        automated_count = sum(1 for step in steps if step.get('action') in automated_actions)
        manual_count = sum(1 for step in steps if step.get('action') in manual_actions)
        
        if automated_count > manual_count * 2:
            return "high"
        elif automated_count > manual_count:
            return "medium"
        else:
            return "low"
    
    def _create_templates(self):
        """Create HTML templates for the review interface"""
        templates_dir = Path("templates")
        templates_dir.mkdir(exist_ok=True)
        
        # Dashboard template
        dashboard_html = '''
<!DOCTYPE html>
<html>
<head>
    <title>{{ title }}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { background: #2c3e50; color: white; padding: 20px; margin: -20px -20px 20px -20px; }
        .stats { display: flex; gap: 20px; margin: 20px 0; }
        .stat-card { background: #ecf0f1; padding: 15px; border-radius: 5px; flex: 1; }
        .suggestions { margin: 20px 0; }
        .suggestion-card { border: 1px solid #bdc3c7; padding: 15px; margin: 10px 0; border-radius: 5px; }
        .confidence-high { border-left: 5px solid #27ae60; }
        .confidence-medium { border-left: 5px solid #f39c12; }
        .confidence-low { border-left: 5px solid #e74c3c; }
        .btn { padding: 8px 16px; margin: 5px; text-decoration: none; border-radius: 3px; }
        .btn-primary { background: #3498db; color: white; }
        .btn-success { background: #27ae60; color: white; }
        .btn-warning { background: #f39c12; color: white; }
    </style>
</head>
<body>
    <div class="header">
        <h1>{{ title }}</h1>
        <p>AI-Powered Playbook Generation Review System</p>
    </div>
    
    <div class="stats">
        <div class="stat-card">
            <h3>Total Suggestions</h3>
            <p>{{ stats.total_suggestions }}</p>
        </div>
        <div class="stat-card">
            <h3>Pending Review</h3>
            <p>{{ stats.pending_count }}</p>
        </div>
        <div class="stat-card">
            <h3>Approval Rate</h3>
            <p>{{ "%.1f"|format(stats.approval_rate * 100) }}%</p>
        </div>
        <div class="stat-card">
            <h3>Avg Confidence</h3>
            <p>{{ "%.1f"|format(stats.average_confidence_score * 100) }}%</p>
        </div>
    </div>
    
    <div class="suggestions">
        <h2>Pending Suggestions ({{ pending_suggestions|length }})</h2>
        {% for suggestion in pending_suggestions %}
        <div class="suggestion-card {% if suggestion.confidence_score > 0.8 %}confidence-high{% elif suggestion.confidence_score > 0.6 %}confidence-medium{% else %}confidence-low{% endif %}">
            <h3>{{ suggestion.title }}</h3>
            <p>{{ suggestion.description }}</p>
            <p><strong>Confidence:</strong> {{ "%.1f"|format(suggestion.confidence_score * 100) }}%</p>
            <p><strong>Created:</strong> {{ suggestion.created_at }}</p>
            <a href="/suggestion/{{ suggestion.suggestion_id }}" class="btn btn-primary">Review</a>
            <a href="/compare/{{ suggestion.suggestion_id }}" class="btn btn-warning">Compare</a>
        </div>
        {% endfor %}
    </div>
</body>
</html>
        '''
        
        with open(templates_dir / "dashboard.html", "w") as f:
            f.write(dashboard_html)
        
        # Review suggestion template
        review_html = '''
<!DOCTYPE html>
<html>
<head>
    <title>{{ title }}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { background: #2c3e50; color: white; padding: 20px; margin: -20px -20px 20px -20px; }
        .content { display: flex; gap: 20px; }
        .main-content { flex: 2; }
        .sidebar { flex: 1; background: #ecf0f1; padding: 20px; border-radius: 5px; }
        .playbook-spec { background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 10px 0; }
        .step { border: 1px solid #dee2e6; padding: 10px; margin: 5px 0; border-radius: 3px; }
        .btn { padding: 10px 20px; margin: 5px; border: none; border-radius: 3px; cursor: pointer; }
        .btn-success { background: #27ae60; color: white; }
        .btn-danger { background: #e74c3c; color: white; }
        .btn-warning { background: #f39c12; color: white; }
        .btn-secondary { background: #95a5a6; color: white; }
        .form-group { margin: 10px 0; }
        .form-control { width: 100%; padding: 8px; border: 1px solid #ccc; border-radius: 3px; }
        textarea.form-control { height: 100px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>{{ title }}</h1>
        <a href="/" class="btn btn-secondary">← Back to Dashboard</a>
    </div>
    
    <div class="content">
        <div class="main-content">
            <h2>Suggestion Details</h2>
            <div class="playbook-spec">
                <h3>{{ suggestion.title }}</h3>
                <p><strong>Description:</strong> {{ suggestion.description }}</p>
                <p><strong>Confidence Score:</strong> {{ "%.1f"|format(suggestion.confidence_score * 100) }}%</p>
                <p><strong>Pattern ID:</strong> {{ suggestion.pattern_id }}</p>
                
                <h4>Playbook Preview</h4>
                <div id="playbook-preview">
                    <p><strong>Name:</strong> {{ suggestion.playbook_spec.name }}</p>
                    <p><strong>Description:</strong> {{ suggestion.playbook_spec.description }}</p>
                    
                    <h5>Parameters ({{ suggestion.playbook_spec.parameters|length }})</h5>
                    {% for param in suggestion.playbook_spec.parameters %}
                    <div class="step">
                        <strong>{{ param.name }}</strong>{% if param.required %} (required){% endif %}
                        <br>{{ param.description }}
                    </div>
                    {% endfor %}
                    
                    <h5>Steps ({{ suggestion.playbook_spec.steps|length }})</h5>
                    {% for step in suggestion.playbook_spec.steps %}
                    <div class="step">
                        <strong>{{ loop.index }}. {{ step.name }}</strong>
                        <br>Action: {{ step.action }}
                        {% if step.args %}
                        <br>Args: {{ step.args }}
                        {% endif %}
                    </div>
                    {% endfor %}
                </div>
            </div>
            
            <h3>Review Actions</h3>
            <form id="review-form">
                <div class="form-group">
                    <label>Reviewer Notes:</label>
                    <textarea id="reviewer-notes" class="form-control" placeholder="Add your review comments..."></textarea>
                </div>
                
                <button type="button" onclick="submitReview('approve')" class="btn btn-success">✓ Approve</button>
                <button type="button" onclick="submitReview('needs_revision')" class="btn btn-warning">⚠ Needs Revision</button>
                <button type="button" onclick="submitReview('reject')" class="btn btn-danger">✗ Reject</button>
            </form>
        </div>
        
        <div class="sidebar">
            <h3>Similar Playbooks</h3>
            {% for similar in similar_playbooks[:3] %}
            <div style="border: 1px solid #ccc; padding: 10px; margin: 10px 0; border-radius: 3px;">
                <h4>{{ similar.title }}</h4>
                <p>Similarity: {{ "%.1f"|format(similar.similarity_score * 100) }}%</p>
                <small>{{ similar.created_at }}</small>
            </div>
            {% endfor %}
            
            <h3>Review History</h3>
            {% for review in review_history[:5] %}
            <div style="border: 1px solid #ccc; padding: 10px; margin: 10px 0; border-radius: 3px;">
                <strong>{{ review.action }}</strong>
                <br><small>{{ review.timestamp }}</small>
                {% if review.reviewer_notes %}
                <br>{{ review.reviewer_notes }}
                {% endif %}
            </div>
            {% endfor %}
        </div>
    </div>
    
    <script>
        async function submitReview(action) {
            const notes = document.getElementById('reviewer-notes').value;
            
            try {
                const response = await fetch('/api/review', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        suggestion_id: '{{ suggestion.suggestion_id }}',
                        action: action,
                        reviewer_notes: notes
                    })
                });
                
                const result = await response.json();
                
                if (response.ok) {
                    alert('Review submitted successfully!');
                    window.location.href = '/';
                } else {
                    alert('Error: ' + result.error);
                }
            } catch (error) {
                alert('Error submitting review: ' + error);
            }
        }
    </script>
</body>
</html>
        '''
        
        with open(templates_dir / "review_suggestion.html", "w") as f:
            f.write(review_html)
        
        # Comparison template
        compare_html = '''
<!DOCTYPE html>
<html>
<head>
    <title>{{ title }}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { background: #2c3e50; color: white; padding: 20px; margin: -20px -20px 20px -20px; }
        .comparison { display: flex; gap: 20px; margin: 20px 0; }
        .comparison-item { flex: 1; border: 1px solid #ccc; padding: 15px; border-radius: 5px; }
        .suggestion { background: #e8f5e8; }
        .existing { background: #f0f8ff; }
        .btn { padding: 10px 20px; margin: 5px; text-decoration: none; border-radius: 3px; }
        .btn-secondary { background: #95a5a6; color: white; }
        .btn-primary { background: #3498db; color: white; }
    </style>
</head>
<body>
    <div class="header">
        <h1>{{ title }}</h1>
        <a href="/" class="btn btn-secondary">← Back to Dashboard</a>
        <a href="/suggestion/{{ suggestion.suggestion_id }}" class="btn btn-primary">Review Suggestion</a>
    </div>
    
    <h2>Playbook Comparison</h2>
    
    {% for comparison in comparisons %}
    <div class="comparison">
        <div class="comparison-item suggestion">
            <h3>🤖 AI Generated Suggestion</h3>
            <h4>{{ suggestion.title }}</h4>
            <p><strong>Confidence:</strong> {{ "%.1f"|format(suggestion.confidence_score * 100) }}%</p>
            <p><strong>Steps:</strong> {{ comparison.differences.step_count.suggestion }}</p>
            <p><strong>Complexity:</strong> {{ comparison.differences.complexity }}</p>
            
            <h5>Advantages:</h5>
            <ul>
                {% for advantage in comparison.advantages.suggestion %}
                <li>{{ advantage }}</li>
                {% endfor %}
            </ul>
        </div>
        
        <div class="comparison-item existing">
            <h3>📋 Existing Playbook</h3>
            <h4>{{ comparison.existing_playbook.title }}</h4>
            <p><strong>Similarity:</strong> {{ "%.1f"|format(comparison.existing_playbook.similarity_score * 100) }}%</p>
            <p><strong>Content Length:</strong> {{ comparison.differences.step_count.existing }} lines</p>
            
            <h5>Advantages:</h5>
            <ul>
                {% for advantage in comparison.advantages.existing %}
                <li>{{ advantage }}</li>
                {% endfor %}
            </ul>
        </div>
    </div>
    
    <div style="text-align: center; margin: 20px 0; padding: 15px; background: #f8f9fa; border-radius: 5px;">
        <h4>Recommendation: {{ comparison.recommendation.replace('_', ' ').title() }}</h4>
    </div>
    {% endfor %}
</body>
</html>
        '''
        
        with open(templates_dir / "compare_playbooks.html", "w") as f:
            f.write(compare_html)
        
        logger.info("📝 Created HTML templates for review interface")
    
    async def start_server(self, host: str = "0.0.0.0", port: int = 8080):
        """Start the review interface server"""
        try:
            import uvicorn
            logger.info(f"🌐 Starting Playbook Review Interface on http://{host}:{port}")
            await uvicorn.run(self.app, host=host, port=port)
        except Exception as e:
            logger.error(f"Failed to start review interface server: {e}")
            raise