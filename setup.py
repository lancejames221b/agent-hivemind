#!/usr/bin/env python3
"""
ClaudeOps hAIveMind - Distributed AI Memory & Coordination System
Setup script for Python package installation
"""

from setuptools import setup, find_packages
import os

# Read the README file
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# Read requirements
with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="claudeops-haivemind",
    version="2.1.1",
    author="Lance James",
    author_email="lancejames@unit221b.com",
    description="Distributed AI agent coordination with persistent collective memory across infrastructure networks",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/lancejames/claudeops-haivemind",
    project_urls={
        "Bug Tracker": "https://github.com/lancejames/claudeops-haivemind/issues",
        "Documentation": "https://github.com/lancejames/claudeops-haivemind#readme",
        "Source Code": "https://github.com/lancejames/claudeops-haivemind",
    },
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "Topic :: System :: Systems Administration",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
        "Framework :: AsyncIO",
        "Topic :: Communications",
        "Topic :: Internet :: WWW/HTTP :: HTTP Servers",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
        ],
        "docs": [
            "sphinx>=5.0.0",
            "sphinx-rtd-theme>=1.0.0",
            "myst-parser>=1.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "haivemind-server=memory_server:main",
            "haivemind-remote=remote_mcp_server:main",
            "haivemind-sync=sync_service:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["config/*.json", "services/*.sh", "INSTALL/*.sh"],
    },
    keywords=[
        "mcp",
        "model-context-protocol", 
        "ai",
        "claude",
        "devops",
        "automation",
        "distributed-systems",
        "memory",
        "coordination",
        "infrastructure",
        "agents",
        "collective-intelligence",
    ],
    zip_safe=False,
)