#!/usr/bin/env python3
"""
MCP Server Templates and Examples
Provides templates and example configurations for creating MCP servers
to be shared in the marketplace.

Author: Lance James, Unit 221B, Inc
Date: August 24, 2025
Version: 1.0.0
"""

import os
import json
import uuid
import base64
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import tempfile
import shutil

class ServerTemplate:
    """Base class for MCP server templates"""
    
    def __init__(self, 
                 name: str,
                 description: str,
                 language: str,
                 category: str = "general"):
        self.name = name
        self.description = description
        self.language = language
        self.category = category
        self.files = {}
        self.metadata = {}
    
    def add_file(self, path: str, content: str):
        """Add a file to the template"""
        self.files[path] = content
    
    def set_metadata(self, **kwargs):
        """Set template metadata"""
        self.metadata.update(kwargs)
    
    def generate_package(self, output_dir: Path) -> Path:
        """Generate a complete server package"""
        package_dir = output_dir / f"{self.name.lower().replace(' ', '_')}_template"
        package_dir.mkdir(parents=True, exist_ok=True)
        
        # Write all files
        for file_path, content in self.files.items():
            full_path = package_dir / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(full_path, 'w') as f:
                f.write(content)
        
        # Create ZIP package
        zip_path = output_dir / f"{self.name.lower().replace(' ', '_')}_template.zip"
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(package_dir):
                for file in files:
                    file_path = Path(root) / file
                    arcname = file_path.relative_to(package_dir)
                    zipf.write(file_path, arcname)
        
        # Clean up directory
        shutil.rmtree(package_dir)
        
        return zip_path

class MarketplaceTemplates:
    """Manager for MCP server templates"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.templates_dir = Path(config.get("templates_directory", "templates/marketplace"))
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize built-in templates
        self.templates = {}
        self._create_builtin_templates()
    
    def _create_builtin_templates(self):
        """Create built-in server templates"""
        
        # Python Basic Template
        python_basic = ServerTemplate(
            name="Python Basic MCP Server",
            description="A basic Python MCP server template with essential tools",
            language="python",
            category="template"
        )
        
        python_basic.add_file("server.py", '''#!/usr/bin/env python3
"""
Basic MCP Server Template
Generated from hAIveMind Marketplace Templates
"""

import asyncio
import json
from typing import Any, Dict, List, Optional
from mcp import McpServer, Tool, Resource
from mcp.types import TextContent, ImageContent, EmbeddedResource

# Server configuration
SERVER_NAME = "Basic MCP Server"
SERVER_VERSION = "1.0.0"

class BasicMCPServer:
    """Basic MCP Server implementation"""
    
    def __init__(self):
        self.server = McpServer(SERVER_NAME)
        self._setup_tools()
        self._setup_resources()
    
    def _setup_tools(self):
        """Setup server tools"""
        
        @self.server.tool("hello")
        async def hello_tool(name: str = "World") -> str:
            """Say hello to someone"""
            return f"Hello, {name}! This is {SERVER_NAME} v{SERVER_VERSION}"
        
        @self.server.tool("echo")
        async def echo_tool(message: str) -> str:
            """Echo back a message"""
            return f"Echo: {message}"
        
        @self.server.tool("get_time")
        async def get_time_tool() -> str:
            """Get current time"""
            from datetime import datetime
            return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        @self.server.tool("calculate")
        async def calculate_tool(expression: str) -> str:
            """Calculate a mathematical expression (basic operations only)"""
            try:
                # Basic safety check - only allow numbers and basic operators
                allowed_chars = set('0123456789+-*/.() ')
                if not all(c in allowed_chars for c in expression):
                    return "Error: Only basic mathematical operations are allowed"
                
                result = eval(expression)
                return f"{expression} = {result}"
            except Exception as e:
                return f"Error calculating '{expression}': {str(e)}"
    
    def _setup_resources(self):
        """Setup server resources"""
        
        @self.server.resource("server://info")
        async def server_info() -> str:
            """Get server information"""
            info = {
                "name": SERVER_NAME,
                "version": SERVER_VERSION,
                "description": "Basic MCP server template",
                "tools": ["hello", "echo", "get_time", "calculate"],
                "resources": ["server://info", "server://status"]
            }
            return json.dumps(info, indent=2)
        
        @self.server.resource("server://status")
        async def server_status() -> str:
            """Get server status"""
            status = {
                "status": "running",
                "timestamp": datetime.now().isoformat(),
                "uptime": "N/A"  # Would track actual uptime in real implementation
            }
            return json.dumps(status, indent=2)
    
    async def run(self):
        """Run the server"""
        async with self.server.stdio_server() as streams:
            await self.server.run(
                streams[0], streams[1], self.server.create_initialization_options()
            )

if __name__ == "__main__":
    server = BasicMCPServer()
    asyncio.run(server.run())
''')
        
        python_basic.add_file("requirements.txt", '''mcp>=1.0.0
asyncio-compat>=0.1.0
''')
        
        python_basic.add_file("config.json", '''{
  "server": {
    "name": "Basic MCP Server",
    "version": "1.0.0",
    "description": "A basic MCP server template",
    "port": 8900,
    "host": "localhost"
  },
  "tools": {
    "hello": {
      "description": "Say hello to someone",
      "parameters": {
        "name": {
          "type": "string",
          "description": "Name to greet",
          "default": "World"
        }
      }
    },
    "echo": {
      "description": "Echo back a message",
      "parameters": {
        "message": {
          "type": "string",
          "description": "Message to echo back",
          "required": true
        }
      }
    },
    "get_time": {
      "description": "Get current time",
      "parameters": {}
    },
    "calculate": {
      "description": "Calculate a mathematical expression",
      "parameters": {
        "expression": {
          "type": "string",
          "description": "Mathematical expression to calculate",
          "required": true
        }
      }
    }
  },
  "resources": {
    "server://info": {
      "description": "Server information"
    },
    "server://status": {
      "description": "Server status"
    }
  }
}''')
        
        python_basic.add_file("README.md", '''# Basic MCP Server Template

A basic MCP (Model Context Protocol) server template with essential tools and resources.

## Features

- **Hello Tool**: Greet users with a personalized message
- **Echo Tool**: Echo back any message
- **Time Tool**: Get current timestamp
- **Calculator Tool**: Perform basic mathematical calculations
- **Server Info**: Get server information and status

## Installation

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the server:
   ```bash
   python server.py
   ```

## Configuration

Edit `config.json` to customize server settings, tools, and resources.

## Usage

This server can be used with any MCP-compatible client. Add it to your client configuration:

```json
{
  "mcpServers": {
    "basic-server": {
      "command": "python",
      "args": ["path/to/server.py"]
    }
  }
}
```

## Customization

This template provides a starting point for creating your own MCP server. You can:

- Add new tools by implementing functions with the `@self.server.tool()` decorator
- Add new resources with the `@self.server.resource()` decorator
- Modify the configuration in `config.json`
- Add additional dependencies in `requirements.txt`

## License

MIT License - feel free to use and modify as needed.
''')
        
        python_basic.set_metadata(
            author="hAIveMind Marketplace",
            author_email="marketplace@haivemind.ai",
            license="MIT",
            keywords=["template", "basic", "starter"],
            tools=[
                {"name": "hello", "description": "Say hello to someone"},
                {"name": "echo", "description": "Echo back a message"},
                {"name": "get_time", "description": "Get current time"},
                {"name": "calculate", "description": "Calculate mathematical expressions"}
            ],
            resources=[
                {"name": "server://info", "description": "Server information"},
                {"name": "server://status", "description": "Server status"}
            ]
        )
        
        self.templates["python_basic"] = python_basic
        
        # Data Processing Template
        data_processing = ServerTemplate(
            name="Data Processing MCP Server",
            description="Template for data processing and analysis MCP servers",
            language="python",
            category="data-processing"
        )
        
        data_processing.add_file("server.py", '''#!/usr/bin/env python3
"""
Data Processing MCP Server Template
Provides tools for data analysis, transformation, and visualization
"""

import asyncio
import json
import csv
import io
from typing import Any, Dict, List, Optional
from mcp import McpServer, Tool, Resource
import pandas as pd
import numpy as np

SERVER_NAME = "Data Processing MCP Server"
SERVER_VERSION = "1.0.0"

class DataProcessingServer:
    """Data processing MCP server implementation"""
    
    def __init__(self):
        self.server = McpServer(SERVER_NAME)
        self.data_cache = {}  # Simple in-memory cache for datasets
        self._setup_tools()
        self._setup_resources()
    
    def _setup_tools(self):
        """Setup data processing tools"""
        
        @self.server.tool("load_csv")
        async def load_csv_tool(data: str, dataset_name: str = "default") -> str:
            """Load CSV data into memory"""
            try:
                df = pd.read_csv(io.StringIO(data))
                self.data_cache[dataset_name] = df
                
                return json.dumps({
                    "success": True,
                    "dataset_name": dataset_name,
                    "shape": df.shape,
                    "columns": df.columns.tolist(),
                    "dtypes": df.dtypes.astype(str).to_dict(),
                    "head": df.head().to_dict()
                }, indent=2)
            except Exception as e:
                return json.dumps({
                    "success": False,
                    "error": str(e)
                })
        
        @self.server.tool("describe_data")
        async def describe_data_tool(dataset_name: str = "default") -> str:
            """Get statistical description of dataset"""
            if dataset_name not in self.data_cache:
                return json.dumps({
                    "success": False,
                    "error": f"Dataset '{dataset_name}' not found"
                })
            
            try:
                df = self.data_cache[dataset_name]
                description = df.describe(include='all')
                
                return json.dumps({
                    "success": True,
                    "dataset_name": dataset_name,
                    "shape": df.shape,
                    "description": description.to_dict(),
                    "missing_values": df.isnull().sum().to_dict(),
                    "memory_usage": df.memory_usage(deep=True).to_dict()
                }, indent=2)
            except Exception as e:
                return json.dumps({
                    "success": False,
                    "error": str(e)
                })
        
        @self.server.tool("filter_data")
        async def filter_data_tool(dataset_name: str, column: str, condition: str, value: str, new_dataset_name: str = None) -> str:
            """Filter dataset based on conditions"""
            if dataset_name not in self.data_cache:
                return json.dumps({
                    "success": False,
                    "error": f"Dataset '{dataset_name}' not found"
                })
            
            try:
                df = self.data_cache[dataset_name]
                
                if column not in df.columns:
                    return json.dumps({
                        "success": False,
                        "error": f"Column '{column}' not found in dataset"
                    })
                
                # Apply filter based on condition
                if condition == "equals":
                    filtered_df = df[df[column] == value]
                elif condition == "greater_than":
                    filtered_df = df[df[column] > float(value)]
                elif condition == "less_than":
                    filtered_df = df[df[column] < float(value)]
                elif condition == "contains":
                    filtered_df = df[df[column].astype(str).str.contains(value, na=False)]
                else:
                    return json.dumps({
                        "success": False,
                        "error": f"Unsupported condition: {condition}"
                    })
                
                # Store filtered data
                result_name = new_dataset_name or f"{dataset_name}_filtered"
                self.data_cache[result_name] = filtered_df
                
                return json.dumps({
                    "success": True,
                    "original_dataset": dataset_name,
                    "filtered_dataset": result_name,
                    "original_shape": df.shape,
                    "filtered_shape": filtered_df.shape,
                    "filter_condition": f"{column} {condition} {value}"
                }, indent=2)
                
            except Exception as e:
                return json.dumps({
                    "success": False,
                    "error": str(e)
                })
        
        @self.server.tool("aggregate_data")
        async def aggregate_data_tool(dataset_name: str, group_by: str, agg_column: str, agg_function: str) -> str:
            """Aggregate data by grouping"""
            if dataset_name not in self.data_cache:
                return json.dumps({
                    "success": False,
                    "error": f"Dataset '{dataset_name}' not found"
                })
            
            try:
                df = self.data_cache[dataset_name]
                
                if group_by not in df.columns or agg_column not in df.columns:
                    return json.dumps({
                        "success": False,
                        "error": "Specified columns not found in dataset"
                    })
                
                # Perform aggregation
                if agg_function == "sum":
                    result = df.groupby(group_by)[agg_column].sum()
                elif agg_function == "mean":
                    result = df.groupby(group_by)[agg_column].mean()
                elif agg_function == "count":
                    result = df.groupby(group_by)[agg_column].count()
                elif agg_function == "max":
                    result = df.groupby(group_by)[agg_column].max()
                elif agg_function == "min":
                    result = df.groupby(group_by)[agg_column].min()
                else:
                    return json.dumps({
                        "success": False,
                        "error": f"Unsupported aggregation function: {agg_function}"
                    })
                
                return json.dumps({
                    "success": True,
                    "dataset_name": dataset_name,
                    "aggregation": f"{agg_function}({agg_column}) by {group_by}",
                    "result": result.to_dict()
                }, indent=2)
                
            except Exception as e:
                return json.dumps({
                    "success": False,
                    "error": str(e)
                })
        
        @self.server.tool("export_csv")
        async def export_csv_tool(dataset_name: str) -> str:
            """Export dataset as CSV"""
            if dataset_name not in self.data_cache:
                return json.dumps({
                    "success": False,
                    "error": f"Dataset '{dataset_name}' not found"
                })
            
            try:
                df = self.data_cache[dataset_name]
                csv_data = df.to_csv(index=False)
                
                return json.dumps({
                    "success": True,
                    "dataset_name": dataset_name,
                    "csv_data": csv_data,
                    "shape": df.shape
                }, indent=2)
                
            except Exception as e:
                return json.dumps({
                    "success": False,
                    "error": str(e)
                })
    
    def _setup_resources(self):
        """Setup data processing resources"""
        
        @self.server.resource("data://datasets")
        async def list_datasets() -> str:
            """List all loaded datasets"""
            datasets_info = {}
            for name, df in self.data_cache.items():
                datasets_info[name] = {
                    "shape": df.shape,
                    "columns": df.columns.tolist(),
                    "dtypes": df.dtypes.astype(str).to_dict()
                }
            
            return json.dumps({
                "loaded_datasets": list(self.data_cache.keys()),
                "count": len(self.data_cache),
                "details": datasets_info
            }, indent=2)
        
        @self.server.resource("data://sample")
        async def sample_data() -> str:
            """Get sample dataset for testing"""
            sample_data = {
                "name": ["Alice", "Bob", "Charlie", "Diana", "Eve"],
                "age": [25, 30, 35, 28, 32],
                "city": ["New York", "London", "Tokyo", "Paris", "Berlin"],
                "salary": [50000, 60000, 70000, 55000, 65000]
            }
            
            return json.dumps({
                "sample_csv": pd.DataFrame(sample_data).to_csv(index=False),
                "description": "Sample dataset with employee information"
            }, indent=2)
    
    async def run(self):
        """Run the server"""
        async with self.server.stdio_server() as streams:
            await self.server.run(
                streams[0], streams[1], self.server.create_initialization_options()
            )

if __name__ == "__main__":
    server = DataProcessingServer()
    asyncio.run(server.run())
''')
        
        data_processing.add_file("requirements.txt", '''mcp>=1.0.0
pandas>=1.5.0
numpy>=1.21.0
''')
        
        data_processing.add_file("config.json", '''{
  "server": {
    "name": "Data Processing MCP Server",
    "version": "1.0.0",
    "description": "MCP server for data processing and analysis",
    "category": "data-processing"
  },
  "tools": {
    "load_csv": {
      "description": "Load CSV data into memory for processing",
      "parameters": {
        "data": {"type": "string", "description": "CSV data as string"},
        "dataset_name": {"type": "string", "description": "Name for the dataset", "default": "default"}
      }
    },
    "describe_data": {
      "description": "Get statistical description of dataset",
      "parameters": {
        "dataset_name": {"type": "string", "description": "Name of dataset to describe", "default": "default"}
      }
    },
    "filter_data": {
      "description": "Filter dataset based on conditions",
      "parameters": {
        "dataset_name": {"type": "string", "description": "Name of dataset to filter"},
        "column": {"type": "string", "description": "Column to filter on"},
        "condition": {"type": "string", "description": "Filter condition", "enum": ["equals", "greater_than", "less_than", "contains"]},
        "value": {"type": "string", "description": "Value to filter by"},
        "new_dataset_name": {"type": "string", "description": "Name for filtered dataset", "required": false}
      }
    },
    "aggregate_data": {
      "description": "Aggregate data by grouping",
      "parameters": {
        "dataset_name": {"type": "string", "description": "Name of dataset to aggregate"},
        "group_by": {"type": "string", "description": "Column to group by"},
        "agg_column": {"type": "string", "description": "Column to aggregate"},
        "agg_function": {"type": "string", "description": "Aggregation function", "enum": ["sum", "mean", "count", "max", "min"]}
      }
    },
    "export_csv": {
      "description": "Export dataset as CSV",
      "parameters": {
        "dataset_name": {"type": "string", "description": "Name of dataset to export"}
      }
    }
  },
  "resources": {
    "data://datasets": {
      "description": "List all loaded datasets"
    },
    "data://sample": {
      "description": "Get sample dataset for testing"
    }
  }
}''')
        
        data_processing.add_file("README.md", '''# Data Processing MCP Server Template

A comprehensive MCP server template for data processing, analysis, and transformation tasks.

## Features

- **CSV Loading**: Load CSV data into memory for processing
- **Data Description**: Get statistical summaries and data info
- **Data Filtering**: Filter datasets based on various conditions
- **Data Aggregation**: Group and aggregate data with common functions
- **CSV Export**: Export processed data back to CSV format
- **Dataset Management**: Track and manage multiple datasets in memory

## Installation

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the server:
   ```bash
   python server.py
   ```

## Usage Examples

### Load and Analyze Data

1. Load CSV data:
   ```
   load_csv(data="name,age,city\\nAlice,25,NYC\\nBob,30,LA", dataset_name="employees")
   ```

2. Get data description:
   ```
   describe_data(dataset_name="employees")
   ```

3. Filter data:
   ```
   filter_data(dataset_name="employees", column="age", condition="greater_than", value="25")
   ```

4. Aggregate data:
   ```
   aggregate_data(dataset_name="employees", group_by="city", agg_column="age", agg_function="mean")
   ```

### Resources

- `data://datasets` - List all loaded datasets
- `data://sample` - Get sample data for testing

## Customization

Extend this template by:

- Adding more data processing functions
- Supporting additional file formats (JSON, Excel, etc.)
- Adding data visualization capabilities
- Implementing machine learning features
- Adding database connectivity

## Dependencies

- pandas: Data manipulation and analysis
- numpy: Numerical computing
- mcp: Model Context Protocol framework

## License

MIT License
''')
        
        data_processing.set_metadata(
            author="hAIveMind Marketplace",
            author_email="marketplace@haivemind.ai",
            license="MIT",
            keywords=["data-processing", "analytics", "csv", "pandas"],
            tools=[
                {"name": "load_csv", "description": "Load CSV data into memory"},
                {"name": "describe_data", "description": "Get statistical description"},
                {"name": "filter_data", "description": "Filter dataset based on conditions"},
                {"name": "aggregate_data", "description": "Aggregate data by grouping"},
                {"name": "export_csv", "description": "Export dataset as CSV"}
            ],
            resources=[
                {"name": "data://datasets", "description": "List loaded datasets"},
                {"name": "data://sample", "description": "Sample dataset"}
            ]
        )
        
        self.templates["data_processing"] = data_processing
        
        # Web Scraping Template
        web_scraping = ServerTemplate(
            name="Web Scraping MCP Server",
            description="Template for web scraping and data extraction MCP servers",
            language="python",
            category="web-scraping"
        )
        
        web_scraping.add_file("server.py", '''#!/usr/bin/env python3
"""
Web Scraping MCP Server Template
Provides tools for web scraping, HTML parsing, and data extraction
"""

import asyncio
import json
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse
from mcp import McpServer, Tool, Resource
import aiohttp
from bs4 import BeautifulSoup
import requests

SERVER_NAME = "Web Scraping MCP Server"
SERVER_VERSION = "1.0.0"

class WebScrapingServer:
    """Web scraping MCP server implementation"""
    
    def __init__(self):
        self.server = McpServer(SERVER_NAME)
        self.session = None
        self._setup_tools()
        self._setup_resources()
    
    async def _get_session(self):
        """Get or create aiohttp session"""
        if self.session is None:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                headers={
                    'User-Agent': 'Mozilla/5.0 (compatible; MCP-WebScraper/1.0)'
                }
            )
        return self.session
    
    def _setup_tools(self):
        """Setup web scraping tools"""
        
        @self.server.tool("fetch_page")
        async def fetch_page_tool(url: str, headers: Dict[str, str] = None) -> str:
            """Fetch a web page and return its content"""
            try:
                session = await self._get_session()
                
                request_headers = headers or {}
                async with session.get(url, headers=request_headers) as response:
                    if response.status == 200:
                        content = await response.text()
                        
                        return json.dumps({
                            "success": True,
                            "url": url,
                            "status_code": response.status,
                            "content_length": len(content),
                            "content_type": response.headers.get('content-type', ''),
                            "content": content[:10000],  # Limit content size
                            "truncated": len(content) > 10000
                        }, indent=2)
                    else:
                        return json.dumps({
                            "success": False,
                            "url": url,
                            "status_code": response.status,
                            "error": f"HTTP {response.status}"
                        })
                        
            except Exception as e:
                return json.dumps({
                    "success": False,
                    "url": url,
                    "error": str(e)
                })
        
        @self.server.tool("extract_text")
        async def extract_text_tool(html: str, selector: str = None) -> str:
            """Extract text from HTML using CSS selectors"""
            try:
                soup = BeautifulSoup(html, 'html.parser')
                
                if selector:
                    elements = soup.select(selector)
                    if elements:
                        texts = [elem.get_text(strip=True) for elem in elements]
                        return json.dumps({
                            "success": True,
                            "selector": selector,
                            "found_elements": len(elements),
                            "texts": texts
                        }, indent=2)
                    else:
                        return json.dumps({
                            "success": False,
                            "selector": selector,
                            "error": "No elements found matching selector"
                        })
                else:
                    # Extract all text
                    text = soup.get_text(strip=True)
                    return json.dumps({
                        "success": True,
                        "text_length": len(text),
                        "text": text[:5000],  # Limit text size
                        "truncated": len(text) > 5000
                    }, indent=2)
                    
            except Exception as e:
                return json.dumps({
                    "success": False,
                    "error": str(e)
                })
        
        @self.server.tool("extract_links")
        async def extract_links_tool(html: str, base_url: str = None) -> str:
            """Extract all links from HTML"""
            try:
                soup = BeautifulSoup(html, 'html.parser')
                links = []
                
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    text = link.get_text(strip=True)
                    
                    # Convert relative URLs to absolute
                    if base_url and not href.startswith(('http://', 'https://')):
                        href = urljoin(base_url, href)
                    
                    links.append({
                        "url": href,
                        "text": text,
                        "title": link.get('title', '')
                    })
                
                return json.dumps({
                    "success": True,
                    "base_url": base_url,
                    "links_found": len(links),
                    "links": links
                }, indent=2)
                
            except Exception as e:
                return json.dumps({
                    "success": False,
                    "error": str(e)
                })
        
        @self.server.tool("extract_images")
        async def extract_images_tool(html: str, base_url: str = None) -> str:
            """Extract all images from HTML"""
            try:
                soup = BeautifulSoup(html, 'html.parser')
                images = []
                
                for img in soup.find_all('img'):
                    src = img.get('src', '')
                    if not src:
                        continue
                    
                    # Convert relative URLs to absolute
                    if base_url and not src.startswith(('http://', 'https://')):
                        src = urljoin(base_url, src)
                    
                    images.append({
                        "src": src,
                        "alt": img.get('alt', ''),
                        "title": img.get('title', ''),
                        "width": img.get('width', ''),
                        "height": img.get('height', '')
                    })
                
                return json.dumps({
                    "success": True,
                    "base_url": base_url,
                    "images_found": len(images),
                    "images": images
                }, indent=2)
                
            except Exception as e:
                return json.dumps({
                    "success": False,
                    "error": str(e)
                })
        
        @self.server.tool("extract_tables")
        async def extract_tables_tool(html: str) -> str:
            """Extract tables from HTML"""
            try:
                soup = BeautifulSoup(html, 'html.parser')
                tables = []
                
                for table in soup.find_all('table'):
                    rows = []
                    for tr in table.find_all('tr'):
                        cells = []
                        for cell in tr.find_all(['td', 'th']):
                            cells.append(cell.get_text(strip=True))
                        if cells:
                            rows.append(cells)
                    
                    if rows:
                        tables.append({
                            "rows": len(rows),
                            "columns": len(rows[0]) if rows else 0,
                            "data": rows
                        })
                
                return json.dumps({
                    "success": True,
                    "tables_found": len(tables),
                    "tables": tables
                }, indent=2)
                
            except Exception as e:
                return json.dumps({
                    "success": False,
                    "error": str(e)
                })
        
        @self.server.tool("scrape_page")
        async def scrape_page_tool(url: str, selectors: Dict[str, str] = None) -> str:
            """Scrape a page and extract specific data using selectors"""
            try:
                # Fetch page
                session = await self._get_session()
                async with session.get(url) as response:
                    if response.status != 200:
                        return json.dumps({
                            "success": False,
                            "url": url,
                            "error": f"HTTP {response.status}"
                        })
                    
                    html = await response.text()
                
                # Parse HTML
                soup = BeautifulSoup(html, 'html.parser')
                extracted_data = {}
                
                if selectors:
                    for key, selector in selectors.items():
                        elements = soup.select(selector)
                        if elements:
                            if len(elements) == 1:
                                extracted_data[key] = elements[0].get_text(strip=True)
                            else:
                                extracted_data[key] = [elem.get_text(strip=True) for elem in elements]
                        else:
                            extracted_data[key] = None
                else:
                    # Default extraction
                    extracted_data = {
                        "title": soup.title.string if soup.title else "",
                        "headings": [h.get_text(strip=True) for h in soup.find_all(['h1', 'h2', 'h3'])],
                        "paragraphs": [p.get_text(strip=True) for p in soup.find_all('p')[:5]],
                        "links_count": len(soup.find_all('a', href=True)),
                        "images_count": len(soup.find_all('img'))
                    }
                
                return json.dumps({
                    "success": True,
                    "url": url,
                    "selectors_used": selectors,
                    "extracted_data": extracted_data
                }, indent=2)
                
            except Exception as e:
                return json.dumps({
                    "success": False,
                    "url": url,
                    "error": str(e)
                })
    
    def _setup_resources(self):
        """Setup web scraping resources"""
        
        @self.server.resource("scraper://status")
        async def scraper_status() -> str:
            """Get scraper status"""
            return json.dumps({
                "server_name": SERVER_NAME,
                "version": SERVER_VERSION,
                "session_active": self.session is not None,
                "supported_formats": ["HTML", "XML"],
                "features": [
                    "Page fetching",
                    "Text extraction",
                    "Link extraction", 
                    "Image extraction",
                    "Table extraction",
                    "CSS selector support"
                ]
            }, indent=2)
        
        @self.server.resource("scraper://selectors")
        async def common_selectors() -> str:
            """Get common CSS selectors for web scraping"""
            selectors = {
                "title": "title, h1",
                "headings": "h1, h2, h3, h4, h5, h6",
                "paragraphs": "p",
                "links": "a[href]",
                "images": "img[src]",
                "tables": "table",
                "lists": "ul, ol",
                "articles": "article, .article, .post",
                "navigation": "nav, .nav, .navigation",
                "footer": "footer, .footer",
                "content": ".content, .main, main, #content"
            }
            
            return json.dumps({
                "common_selectors": selectors,
                "tips": [
                    "Use specific selectors for better results",
                    "Combine selectors with commas for multiple elements",
                    "Use class selectors (.class) and ID selectors (#id)",
                    "Test selectors in browser dev tools first"
                ]
            }, indent=2)
    
    async def run(self):
        """Run the server"""
        try:
            async with self.server.stdio_server() as streams:
                await self.server.run(
                    streams[0], streams[1], self.server.create_initialization_options()
                )
        finally:
            if self.session:
                await self.session.close()

if __name__ == "__main__":
    server = WebScrapingServer()
    asyncio.run(server.run())
''')
        
        web_scraping.add_file("requirements.txt", '''mcp>=1.0.0
aiohttp>=3.8.0
beautifulsoup4>=4.11.0
requests>=2.28.0
lxml>=4.9.0
''')
        
        web_scraping.add_file("README.md", '''# Web Scraping MCP Server Template

A comprehensive MCP server template for web scraping, HTML parsing, and data extraction.

## Features

- **Page Fetching**: Download web pages with custom headers
- **Text Extraction**: Extract text using CSS selectors
- **Link Extraction**: Find and extract all links from pages
- **Image Extraction**: Extract image information and URLs
- **Table Extraction**: Parse HTML tables into structured data
- **Smart Scraping**: Extract specific data using custom selectors

## Installation

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the server:
   ```bash
   python server.py
   ```

## Usage Examples

### Basic Page Scraping

1. Fetch a web page:
   ```
   fetch_page(url="https://example.com")
   ```

2. Extract text from specific elements:
   ```
   extract_text(html="<html>...</html>", selector="h1, h2")
   ```

3. Extract all links:
   ```
   extract_links(html="<html>...</html>", base_url="https://example.com")
   ```

### Advanced Scraping

1. Scrape with custom selectors:
   ```
   scrape_page(url="https://example.com", selectors={
     "title": "h1",
     "price": ".price",
     "description": ".description p"
   })
   ```

### Resources

- `scraper://status` - Get scraper status and capabilities
- `scraper://selectors` - Common CSS selectors and tips

## Customization

Extend this template by:

- Adding support for JavaScript-rendered pages (Selenium)
- Implementing rate limiting and politeness delays
- Adding proxy support for large-scale scraping
- Supporting authentication and session management
- Adding data export formats (CSV, JSON, XML)

## Best Practices

- Respect robots.txt files
- Implement rate limiting to avoid overwhelming servers
- Use appropriate User-Agent strings
- Handle errors gracefully
- Cache responses when appropriate

## Dependencies

- aiohttp: Async HTTP client
- beautifulsoup4: HTML parsing
- requests: HTTP library
- lxml: XML/HTML parser

## License

MIT License
''')
        
        web_scraping.set_metadata(
            author="hAIveMind Marketplace",
            author_email="marketplace@haivemind.ai",
            license="MIT",
            keywords=["web-scraping", "html-parsing", "data-extraction"],
            tools=[
                {"name": "fetch_page", "description": "Fetch web page content"},
                {"name": "extract_text", "description": "Extract text using CSS selectors"},
                {"name": "extract_links", "description": "Extract all links from HTML"},
                {"name": "extract_images", "description": "Extract image information"},
                {"name": "extract_tables", "description": "Extract HTML tables"},
                {"name": "scrape_page", "description": "Scrape page with custom selectors"}
            ]
        )
        
        self.templates["web_scraping"] = web_scraping
    
    def get_template(self, template_id: str) -> Optional[ServerTemplate]:
        """Get a specific template"""
        return self.templates.get(template_id)
    
    def list_templates(self) -> List[Dict[str, Any]]:
        """List all available templates"""
        template_list = []
        
        for template_id, template in self.templates.items():
            template_info = {
                "id": template_id,
                "name": template.name,
                "description": template.description,
                "language": template.language,
                "category": template.category,
                "metadata": template.metadata,
                "files": list(template.files.keys())
            }
            template_list.append(template_info)
        
        return template_list
    
    def generate_template_package(self, template_id: str, output_dir: Path = None) -> Optional[Path]:
        """Generate a complete package for a template"""
        template = self.get_template(template_id)
        if not template:
            return None
        
        if output_dir is None:
            output_dir = self.templates_dir / "generated"
            output_dir.mkdir(parents=True, exist_ok=True)
        
        return template.generate_package(output_dir)
    
    def create_custom_template(self, 
                             name: str,
                             description: str,
                             language: str,
                             category: str,
                             files: Dict[str, str],
                             metadata: Dict[str, Any] = None) -> str:
        """Create a custom template"""
        template_id = f"custom_{uuid.uuid4().hex[:8]}"
        
        template = ServerTemplate(name, description, language, category)
        
        for file_path, content in files.items():
            template.add_file(file_path, content)
        
        if metadata:
            template.set_metadata(**metadata)
        
        self.templates[template_id] = template
        
        return template_id
    
    def get_template_examples(self) -> Dict[str, Any]:
        """Get example configurations for different server types"""
        return {
            "basic_python": {
                "name": "My Basic Server",
                "description": "A simple MCP server with basic tools",
                "language": "python",
                "category": "general",
                "template": "python_basic"
            },
            "data_processor": {
                "name": "CSV Data Processor",
                "description": "Process and analyze CSV data files",
                "language": "python",
                "category": "data-processing",
                "template": "data_processing"
            },
            "web_scraper": {
                "name": "News Scraper",
                "description": "Scrape news articles from websites",
                "language": "python",
                "category": "web-scraping",
                "template": "web_scraping"
            }
        }

def create_marketplace_templates(config: Dict[str, Any]) -> MarketplaceTemplates:
    """Create and configure marketplace templates"""
    return MarketplaceTemplates(config)

if __name__ == "__main__":
    # Example usage
    config = {
        "templates_directory": "templates/marketplace"
    }
    
    templates = create_marketplace_templates(config)
    
    print("Available templates:")
    for template in templates.list_templates():
        print(f"- {template['id']}: {template['name']} ({template['language']})")
    
    # Generate a template package
    output_dir = Path("output/templates")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    package_path = templates.generate_template_package("python_basic", output_dir)
    if package_path:
        print(f"Generated template package: {package_path}")