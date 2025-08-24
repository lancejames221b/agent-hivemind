#!/usr/bin/env python3
"""
Confluence Integration for Playbook Import

This module provides seamless Confluence integration for automated playbook ingestion:
- Confluence API integration with authentication management
- Automatic detection and parsing of runbooks/procedures
- Convert Confluence pages to structured playbook format
- Scheduled sync for keeping playbooks up to date
- Mapping Confluence spaces to playbook categories
- Handle embedded images, tables, and formatting
- Version control integration (track changes from Confluence)
- Bulk import with conflict resolution
- hAIveMind awareness integration
"""

import asyncio
import json
import logging
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urljoin, urlparse

import httpx
import yaml
from bs4 import BeautifulSoup

from database import ControlDatabase
from playbook_engine import PlaybookEngine, load_playbook_content, PlaybookValidationError

logger = logging.getLogger(__name__)

class ConfluenceError(Exception):
    """Base exception for Confluence integration errors"""
    pass

class ConfluenceAuthError(ConfluenceError):
    """Authentication error with Confluence"""
    pass

class ConfluenceParseError(ConfluenceError):
    """Error parsing Confluence content"""
    pass

class ConfluencePageInfo:
    """Information about a Confluence page"""
    def __init__(self, page_id: str, title: str, space_key: str, 
                 version: int, last_modified: datetime, 
                 content_url: str, web_url: str):
        self.page_id = page_id
        self.title = title
        self.space_key = space_key
        self.version = version
        self.last_modified = last_modified
        self.content_url = content_url
        self.web_url = web_url
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            'page_id': self.page_id,
            'title': self.title,
            'space_key': self.space_key,
            'version': self.version,
            'last_modified': self.last_modified.isoformat(),
            'content_url': self.content_url,
            'web_url': self.web_url
        }

class ConfluencePlaybook:
    """A playbook extracted from Confluence"""
    def __init__(self, page_info: ConfluencePageInfo, playbook_spec: Dict[str, Any], 
                 raw_content: str, extracted_metadata: Dict[str, Any]):
        self.page_info = page_info
        self.playbook_spec = playbook_spec
        self.raw_content = raw_content
        self.extracted_metadata = extracted_metadata
        
    def to_yaml(self) -> str:
        """Convert playbook spec to YAML format"""
        return yaml.dump(self.playbook_spec, default_flow_style=False, sort_keys=False)
        
    def to_json(self) -> str:
        """Convert playbook spec to JSON format"""
        return json.dumps(self.playbook_spec, indent=2)

class ConfluenceIntegration:
    """Main Confluence integration class"""
    
    def __init__(self, config: Dict[str, Any], database: ControlDatabase, 
                 haivemind_storage=None):
        self.config = config
        self.database = database
        self.haivemind_storage = haivemind_storage
        self.playbook_engine = PlaybookEngine(allow_unsafe_shell=False)
        
        # Confluence connection settings
        self.base_url = config.get('url', '').rstrip('/')
        self.username = config.get('credentials', {}).get('username')
        self.api_token = config.get('credentials', {}).get('token')
        self.spaces = config.get('spaces', [])
        self.enabled = config.get('enabled', False)
        
        # Space to category mapping
        self.space_category_mapping = config.get('space_category_mapping', {
            'INFRA': 'infrastructure',
            'DEVOPS': 'devops',
            'DOCS': 'documentation',
            'EWITNESS': 'monitoring'
        })
        
        # Playbook detection patterns
        self.playbook_patterns = [
            r'(?i)runbook',
            r'(?i)playbook',
            r'(?i)procedure',
            r'(?i)how\s*to',
            r'(?i)step\s*by\s*step',
            r'(?i)troubleshoot',
            r'(?i)deployment',
            r'(?i)installation',
            r'(?i)configuration',
            r'(?i)maintenance'
        ]
        
        # HTTP client for API calls
        self.client = None
        
    async def __aenter__(self):
        """Async context manager entry"""
        if not self.enabled:
            raise ConfluenceError("Confluence integration is disabled")
            
        if not all([self.base_url, self.username, self.api_token]):
            raise ConfluenceAuthError("Missing Confluence credentials")
            
        # Create HTTP client with authentication
        auth = httpx.BasicAuth(self.username, self.api_token)
        self.client = httpx.AsyncClient(
            auth=auth,
            timeout=30.0,
            headers={
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
        )
        
        # Test connection
        await self._test_connection()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.client:
            await self.client.aclose()
            
    async def _test_connection(self) -> None:
        """Test Confluence API connection"""
        try:
            url = f"{self.base_url}/rest/api/user/current"
            response = await self.client.get(url)
            response.raise_for_status()
            
            user_info = response.json()
            logger.info(f"Connected to Confluence as {user_info.get('displayName', 'Unknown')}")
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise ConfluenceAuthError("Invalid Confluence credentials")
            raise ConfluenceError(f"Confluence API error: {e}")
        except Exception as e:
            raise ConfluenceError(f"Failed to connect to Confluence: {e}")
            
    async def discover_playbook_pages(self, space_key: Optional[str] = None) -> List[ConfluencePageInfo]:
        """Discover pages that might contain playbooks/runbooks"""
        spaces_to_search = [space_key] if space_key else self.spaces
        all_pages = []
        
        for space in spaces_to_search:
            logger.info(f"Discovering playbook pages in space: {space}")
            
            try:
                # Search for pages with playbook-related terms
                search_results = await self._search_pages_in_space(space)
                
                for page_data in search_results:
                    page_info = await self._get_page_info(page_data['id'])
                    if page_info and self._is_likely_playbook(page_info.title):
                        all_pages.append(page_info)
                        
            except Exception as e:
                logger.error(f"Error discovering pages in space {space}: {e}")
                continue
                
        logger.info(f"Discovered {len(all_pages)} potential playbook pages")
        return all_pages
        
    async def _search_pages_in_space(self, space_key: str) -> List[Dict[str, Any]]:
        """Search for pages in a specific space"""
        url = f"{self.base_url}/rest/api/content"
        params = {
            'spaceKey': space_key,
            'type': 'page',
            'status': 'current',
            'limit': 100,
            'expand': 'version,space'
        }
        
        all_pages = []
        start = 0
        
        while True:
            params['start'] = start
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            pages = data.get('results', [])
            
            if not pages:
                break
                
            all_pages.extend(pages)
            
            if len(pages) < params['limit']:
                break
                
            start += params['limit']
            
        return all_pages
        
    async def _get_page_info(self, page_id: str) -> Optional[ConfluencePageInfo]:
        """Get detailed information about a page"""
        try:
            url = f"{self.base_url}/rest/api/content/{page_id}"
            params = {
                'expand': 'version,space,body.storage'
            }
            
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            return ConfluencePageInfo(
                page_id=data['id'],
                title=data['title'],
                space_key=data['space']['key'],
                version=data['version']['number'],
                last_modified=datetime.fromisoformat(
                    data['version']['when'].replace('Z', '+00:00')
                ),
                content_url=f"{self.base_url}/rest/api/content/{page_id}",
                web_url=f"{self.base_url}{data['_links']['webui']}"
            )
            
        except Exception as e:
            logger.error(f"Error getting page info for {page_id}: {e}")
            return None
            
    def _is_likely_playbook(self, title: str) -> bool:
        """Check if a page title suggests it contains a playbook"""
        for pattern in self.playbook_patterns:
            if re.search(pattern, title):
                return True
        return False
        
    async def extract_playbook_from_page(self, page_info: ConfluencePageInfo) -> Optional[ConfluencePlaybook]:
        """Extract a playbook from a Confluence page"""
        try:
            # Get page content
            url = f"{self.base_url}/rest/api/content/{page_info.page_id}"
            params = {
                'expand': 'body.storage,version,space'
            }
            
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            raw_html = data['body']['storage']['value']
            
            # Parse HTML content
            soup = BeautifulSoup(raw_html, 'html.parser')
            
            # Extract playbook structure
            playbook_spec = await self._parse_confluence_content(soup, page_info)
            
            # Extract metadata
            metadata = {
                'source': 'confluence',
                'confluence_page_id': page_info.page_id,
                'confluence_space': page_info.space_key,
                'confluence_url': page_info.web_url,
                'confluence_version': page_info.version,
                'last_modified': page_info.last_modified.isoformat(),
                'extracted_at': datetime.utcnow().isoformat()
            }
            
            return ConfluencePlaybook(
                page_info=page_info,
                playbook_spec=playbook_spec,
                raw_content=raw_html,
                extracted_metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Error extracting playbook from page {page_info.page_id}: {e}")
            return None
            
    async def _parse_confluence_content(self, soup: BeautifulSoup, 
                                       page_info: ConfluencePageInfo) -> Dict[str, Any]:
        """Parse Confluence HTML content into playbook format"""
        
        # Basic playbook structure
        playbook_spec = {
            'version': 1,
            'name': page_info.title,
            'category': self.space_category_mapping.get(page_info.space_key, 'general'),
            'description': self._extract_description(soup),
            'parameters': self._extract_parameters(soup),
            'prerequisites': self._extract_prerequisites(soup),
            'steps': self._extract_steps(soup)
        }
        
        # Add metadata
        playbook_spec['metadata'] = {
            'source': 'confluence',
            'confluence_page_id': page_info.page_id,
            'confluence_space': page_info.space_key,
            'confluence_url': page_info.web_url,
            'confluence_version': page_info.version,
            'imported_at': datetime.utcnow().isoformat()
        }
        
        return playbook_spec
        
    def _extract_description(self, soup: BeautifulSoup) -> str:
        """Extract description from the first paragraph or summary"""
        # Look for first paragraph
        first_para = soup.find('p')
        if first_para:
            return first_para.get_text().strip()
            
        # Look for summary macro
        summary = soup.find('ac:structured-macro', {'ac:name': 'info'})
        if summary:
            return summary.get_text().strip()
            
        return "Imported from Confluence"
        
    def _extract_parameters(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract parameters from tables or structured content"""
        parameters = []
        
        # Look for parameter tables
        tables = soup.find_all('table')
        for table in tables:
            headers = [th.get_text().strip().lower() for th in table.find_all('th')]
            
            if any(keyword in ' '.join(headers) for keyword in ['parameter', 'variable', 'input']):
                rows = table.find_all('tr')[1:]  # Skip header row
                
                for row in rows:
                    cells = [td.get_text().strip() for td in row.find_all('td')]
                    if len(cells) >= 2:
                        param = {
                            'name': cells[0],
                            'description': cells[1] if len(cells) > 1 else '',
                            'required': 'required' in cells[2].lower() if len(cells) > 2 else False
                        }
                        parameters.append(param)
                        
        return parameters
        
    def _extract_prerequisites(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract prerequisites from structured content"""
        prerequisites = []
        
        # Look for prerequisites section
        prereq_headers = soup.find_all(['h1', 'h2', 'h3', 'h4'], 
                                      string=re.compile(r'(?i)prerequisite|requirement|before'))
        
        for header in prereq_headers:
            # Get the next sibling elements until next header
            current = header.next_sibling
            while current and current.name not in ['h1', 'h2', 'h3', 'h4']:
                if current.name == 'ul':
                    for li in current.find_all('li'):
                        prereq_text = li.get_text().strip()
                        if prereq_text:
                            prerequisites.append({
                                'type': 'manual_check',
                                'description': prereq_text
                            })
                current = current.next_sibling
                
        return prerequisites
        
    def _extract_steps(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract steps from ordered lists, numbered sections, or procedures"""
        steps = []
        step_id = 1
        
        # Look for ordered lists
        ordered_lists = soup.find_all('ol')
        for ol in ordered_lists:
            for li in ol.find_all('li', recursive=False):
                step = self._parse_step_content(li, f"step_{step_id}")
                if step:
                    steps.append(step)
                    step_id += 1
                    
        # Look for numbered headings if no ordered lists found
        if not steps:
            numbered_headers = soup.find_all(['h1', 'h2', 'h3', 'h4'], 
                                           string=re.compile(r'^\d+\.'))
            
            for header in numbered_headers:
                step = self._parse_header_step(header, f"step_{step_id}")
                if step:
                    steps.append(step)
                    step_id += 1
                    
        # If still no steps, create a single step with all content
        if not steps:
            content = soup.get_text().strip()
            if content:
                steps.append({
                    'id': 'step_1',
                    'name': 'Execute procedure',
                    'action': 'noop',
                    'args': {
                        'message': 'Manual procedure - follow Confluence page instructions'
                    },
                    'description': content[:500] + '...' if len(content) > 500 else content
                })
                
        return steps
        
    def _parse_step_content(self, li_element, step_id: str) -> Optional[Dict[str, Any]]:
        """Parse a list item into a playbook step"""
        text = li_element.get_text().strip()
        if not text:
            return None
            
        # Try to detect action type from content
        action = 'noop'
        args = {'message': text}
        
        # Check for shell commands
        code_blocks = li_element.find_all('code')
        if code_blocks:
            # If there's a code block, it might be a shell command
            code_text = code_blocks[0].get_text().strip()
            if code_text and not any(char in code_text for char in ['<', '>', 'http']):
                action = 'shell'
                args = {'command': code_text}
                
        # Check for HTTP requests
        if any(keyword in text.lower() for keyword in ['curl', 'wget', 'http', 'api']):
            # Try to extract URL
            url_match = re.search(r'https?://[^\s]+', text)
            if url_match:
                action = 'http_request'
                args = {
                    'url': url_match.group(),
                    'method': 'GET'
                }
                
        return {
            'id': step_id,
            'name': text[:50] + '...' if len(text) > 50 else text,
            'action': action,
            'args': args,
            'description': text
        }
        
    def _parse_header_step(self, header, step_id: str) -> Optional[Dict[str, Any]]:
        """Parse a numbered header into a playbook step"""
        title = header.get_text().strip()
        
        # Get content until next header
        content_parts = []
        current = header.next_sibling
        
        while current and current.name not in ['h1', 'h2', 'h3', 'h4']:
            if hasattr(current, 'get_text'):
                text = current.get_text().strip()
                if text:
                    content_parts.append(text)
            current = current.next_sibling
            
        content = ' '.join(content_parts)
        
        return {
            'id': step_id,
            'name': title,
            'action': 'noop',
            'args': {
                'message': content or 'Manual step - refer to Confluence page'
            },
            'description': content
        }
        
    async def import_playbook(self, confluence_playbook: ConfluencePlaybook, 
                            created_by: Optional[int] = None,
                            force_update: bool = False) -> Tuple[int, int]:
        """Import a Confluence playbook into the database"""
        
        # Check if playbook already exists
        existing_playbooks = self.database.list_playbooks()
        existing_playbook = None
        
        for pb in existing_playbooks:
            if (pb.get('name') == confluence_playbook.page_info.title or
                confluence_playbook.extracted_metadata.get('confluence_page_id') in str(pb.get('tags', []))):
                existing_playbook = pb
                break
                
        if existing_playbook and not force_update:
            logger.info(f"Playbook '{confluence_playbook.page_info.title}' already exists")
            return existing_playbook['id'], existing_playbook['latest_version_id']
            
        try:
            # Validate playbook structure
            self.playbook_engine.validate(confluence_playbook.playbook_spec)
            
            # Create or update playbook
            if existing_playbook:
                playbook_id = existing_playbook['id']
                logger.info(f"Updating existing playbook: {confluence_playbook.page_info.title}")
            else:
                # Create new playbook
                tags = [
                    'confluence',
                    confluence_playbook.page_info.space_key.lower(),
                    'imported',
                    confluence_playbook.page_info.page_id
                ]
                
                playbook_id = self.database.create_playbook(
                    name=confluence_playbook.page_info.title,
                    category=confluence_playbook.playbook_spec['category'],
                    created_by=created_by,
                    tags=tags
                )
                logger.info(f"Created new playbook: {confluence_playbook.page_info.title}")
                
            # Add new version
            version_id = self.database.add_playbook_version(
                playbook_id=playbook_id,
                content=confluence_playbook.to_yaml(),
                format='yaml',
                metadata=confluence_playbook.extracted_metadata,
                changelog=f"Imported from Confluence page (version {confluence_playbook.page_info.version})",
                created_by=created_by
            )
            
            # Store in hAIveMind if available
            if self.haivemind_storage:
                await self._store_in_haivemind(confluence_playbook, playbook_id, version_id)
                
            return playbook_id, version_id
            
        except PlaybookValidationError as e:
            logger.error(f"Playbook validation failed for '{confluence_playbook.page_info.title}': {e}")
            raise ConfluenceParseError(f"Invalid playbook structure: {e}")
            
    async def _store_in_haivemind(self, confluence_playbook: ConfluencePlaybook, 
                                 playbook_id: int, version_id: int) -> None:
        """Store playbook in hAIveMind for searchable memory"""
        try:
            content = f"""
Confluence Playbook: {confluence_playbook.page_info.title}

Source: {confluence_playbook.page_info.web_url}
Space: {confluence_playbook.page_info.space_key}
Category: {confluence_playbook.playbook_spec['category']}
Description: {confluence_playbook.playbook_spec['description']}

Steps:
{yaml.dump(confluence_playbook.playbook_spec['steps'], default_flow_style=False)}

Full Playbook Specification:
{confluence_playbook.to_yaml()}
"""
            
            await self.haivemind_storage.store_memory(
                content=content,
                category='runbooks',
                context=f"Confluence Playbook: {confluence_playbook.page_info.title}",
                metadata={
                    'type': 'confluence_playbook',
                    'playbook_id': playbook_id,
                    'version_id': version_id,
                    'confluence_page_id': confluence_playbook.page_info.page_id,
                    'confluence_space': confluence_playbook.page_info.space_key,
                    'confluence_url': confluence_playbook.page_info.web_url,
                    'confluence_version': confluence_playbook.page_info.version,
                    'category': confluence_playbook.playbook_spec['category'],
                    'step_count': len(confluence_playbook.playbook_spec['steps']),
                    'has_parameters': len(confluence_playbook.playbook_spec.get('parameters', [])) > 0,
                    'imported_at': datetime.utcnow().isoformat()
                },
                tags=[
                    'confluence',
                    'playbook',
                    'runbook',
                    confluence_playbook.page_info.space_key.lower(),
                    confluence_playbook.playbook_spec['category'],
                    'automated_import'
                ]
            )
            
            # Broadcast to hAIveMind network
            if hasattr(self.haivemind_storage, 'broadcast_discovery'):
                await self.haivemind_storage.broadcast_discovery(
                    message=f"New Confluence playbook imported: {confluence_playbook.page_info.title}",
                    category='runbooks',
                    severity='info',
                    details={
                        'playbook_name': confluence_playbook.page_info.title,
                        'confluence_space': confluence_playbook.page_info.space_key,
                        'confluence_url': confluence_playbook.page_info.web_url,
                        'category': confluence_playbook.playbook_spec['category'],
                        'step_count': len(confluence_playbook.playbook_spec['steps'])
                    }
                )
                
        except Exception as e:
            logger.error(f"Failed to store playbook in hAIveMind: {e}")
            # Don't fail the import if hAIveMind storage fails
            
    async def bulk_import_from_space(self, space_key: str, 
                                   created_by: Optional[int] = None,
                                   force_update: bool = False) -> Dict[str, Any]:
        """Bulk import all playbooks from a Confluence space"""
        results = {
            'space_key': space_key,
            'discovered_pages': 0,
            'successful_imports': 0,
            'failed_imports': 0,
            'skipped_imports': 0,
            'imported_playbooks': [],
            'errors': []
        }
        
        try:
            # Discover playbook pages
            pages = await self.discover_playbook_pages(space_key)
            results['discovered_pages'] = len(pages)
            
            logger.info(f"Starting bulk import of {len(pages)} pages from space {space_key}")
            
            for page_info in pages:
                try:
                    # Extract playbook
                    confluence_playbook = await self.extract_playbook_from_page(page_info)
                    if not confluence_playbook:
                        results['failed_imports'] += 1
                        results['errors'].append(f"Failed to extract playbook from page: {page_info.title}")
                        continue
                        
                    # Import playbook
                    playbook_id, version_id = await self.import_playbook(
                        confluence_playbook, created_by, force_update
                    )
                    
                    results['successful_imports'] += 1
                    results['imported_playbooks'].append({
                        'playbook_id': playbook_id,
                        'version_id': version_id,
                        'title': page_info.title,
                        'confluence_page_id': page_info.page_id,
                        'confluence_url': page_info.web_url
                    })
                    
                    logger.info(f"Successfully imported: {page_info.title}")
                    
                except Exception as e:
                    results['failed_imports'] += 1
                    error_msg = f"Failed to import page '{page_info.title}': {str(e)}"
                    results['errors'].append(error_msg)
                    logger.error(error_msg)
                    
        except Exception as e:
            error_msg = f"Bulk import failed for space {space_key}: {str(e)}"
            results['errors'].append(error_msg)
            logger.error(error_msg)
            
        logger.info(f"Bulk import completed for space {space_key}: "
                   f"{results['successful_imports']} successful, "
                   f"{results['failed_imports']} failed, "
                   f"{results['skipped_imports']} skipped")
                   
        return results
        
    async def sync_playbook_updates(self, max_age_hours: int = 24) -> Dict[str, Any]:
        """Sync updates from Confluence for existing playbooks"""
        results = {
            'checked_playbooks': 0,
            'updated_playbooks': 0,
            'failed_updates': 0,
            'no_changes': 0,
            'errors': []
        }
        
        try:
            # Get all playbooks with Confluence metadata
            all_playbooks = self.database.list_playbooks()
            confluence_playbooks = []
            
            for pb in all_playbooks:
                if 'confluence' in pb.get('tags', []):
                    confluence_playbooks.append(pb)
                    
            results['checked_playbooks'] = len(confluence_playbooks)
            logger.info(f"Checking {len(confluence_playbooks)} Confluence playbooks for updates")
            
            cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
            
            for pb in confluence_playbooks:
                try:
                    # Get latest version to check Confluence metadata
                    if not pb.get('latest_version_id'):
                        continue
                        
                    version = self.database.get_playbook_version(pb['latest_version_id'])
                    if not version:
                        continue
                        
                    metadata = version.get('metadata', {})
                    confluence_page_id = metadata.get('confluence_page_id')
                    
                    if not confluence_page_id:
                        continue
                        
                    # Get current page info from Confluence
                    page_info = await self._get_page_info(confluence_page_id)
                    if not page_info:
                        results['failed_updates'] += 1
                        results['errors'].append(f"Could not fetch page info for {pb['name']}")
                        continue
                        
                    # Check if page has been updated since last import
                    last_import_version = metadata.get('confluence_version', 0)
                    
                    if page_info.version <= last_import_version:
                        results['no_changes'] += 1
                        continue
                        
                    # Check if update is recent enough
                    if page_info.last_modified < cutoff_time:
                        results['no_changes'] += 1
                        continue
                        
                    # Extract and import updated playbook
                    confluence_playbook = await self.extract_playbook_from_page(page_info)
                    if not confluence_playbook:
                        results['failed_updates'] += 1
                        results['errors'].append(f"Failed to extract updated playbook: {pb['name']}")
                        continue
                        
                    # Import as update
                    await self.import_playbook(confluence_playbook, force_update=True)
                    
                    results['updated_playbooks'] += 1
                    logger.info(f"Updated playbook: {pb['name']} (Confluence version {page_info.version})")
                    
                except Exception as e:
                    results['failed_updates'] += 1
                    error_msg = f"Failed to update playbook '{pb['name']}': {str(e)}"
                    results['errors'].append(error_msg)
                    logger.error(error_msg)
                    
        except Exception as e:
            error_msg = f"Sync updates failed: {str(e)}"
            results['errors'].append(error_msg)
            logger.error(error_msg)
            
        logger.info(f"Sync completed: {results['updated_playbooks']} updated, "
                   f"{results['no_changes']} no changes, {results['failed_updates']} failed")
                   
        return results
        
    async def get_sync_status(self) -> Dict[str, Any]:
        """Get status of Confluence integration and sync"""
        status = {
            'enabled': self.enabled,
            'connected': False,
            'spaces_configured': len(self.spaces),
            'total_confluence_playbooks': 0,
            'last_sync': None,
            'connection_error': None
        }
        
        if not self.enabled:
            return status
            
        try:
            # Test connection
            await self._test_connection()
            status['connected'] = True
            
            # Count Confluence playbooks
            all_playbooks = self.database.list_playbooks()
            confluence_count = sum(1 for pb in all_playbooks if 'confluence' in pb.get('tags', []))
            status['total_confluence_playbooks'] = confluence_count
            
        except Exception as e:
            status['connection_error'] = str(e)
            
        return status