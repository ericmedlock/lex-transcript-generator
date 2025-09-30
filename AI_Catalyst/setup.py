from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="ai-catalyst",
    version="0.1.0",
    author="Eric Medlock",
    description="Reusable AI components framework for LLM applications",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ericmedlock/AI_Catalyst",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.9",
    install_requires=[
        "asyncpg>=0.28.0",
        "aiohttp>=3.8.0",
        "pyyaml>=6.0",
        "psutil>=5.9.0",
        "openai>=1.0.0",
        "regex>=2023.0.0",
        "pandas>=2.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
        ],
    },
)