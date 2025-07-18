#!/usr/bin/env python3
"""Setup script for OVERKILL Python configurator"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="overkill",
    version="3.0.0",
    author="OVERKILL Team",
    author_email="overkill@example.com",
    description="Professional media center configuration for Raspberry Pi 5",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/flashingcursor/overkill-pi",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Multimedia :: Video",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: POSIX :: Linux",
    ],
    python_requires=">=3.9",
    install_requires=[
        "click>=8.0",
        "rich>=13.0",
        "pyyaml>=6.0",
        "psutil>=5.9",
        "requests>=2.28",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0",
            "pytest-cov>=4.0",
            "black>=23.0",
            "flake8>=6.0",
            "mypy>=1.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "overkill=overkill.configurator:main",
        ],
    },
    package_data={
        "overkill": ["data/*.yaml", "templates/*.conf"],
    },
    include_package_data=True,
)