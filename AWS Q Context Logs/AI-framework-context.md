# AI_Catalyst Framework - Project Context

## Framework Overview
AI_Catalyst is a production-ready AI components framework with enterprise-grade security, resilience, and async performance optimizations. This project uses AI_Catalyst for AI/ML operations.

## Installation
```bash
pip install ai-catalyst
```

## Core Components Available

### 1. LLM Provider (Three-Tier System)
```python
from ai_catalyst import LLMProvider

# Basic usage
llm = LLMProvider()
response = await llm.generate_async("Your prompt here")

# With security components
llm = LLMProvider(
    key_vault=key_vault,
    rate_limiter=rate_limiter,
    audit_logger=audit_logger
)
```

### 2. PII Detection & Scrubbing
```python
from ai_catalyst import PIIProcessor

pii = PIIProcessor()
clean_text = await pii.scrub_text_async("Sensitive data here")
# Automatically replaces PII with placeholders: <NAME>, <PHONE>, <EMAIL>, etc.
```

### 3. File Processing (Async Streaming)
```python
from ai_catalyst import FileProcessor

processor = FileProcessor()
async for item in processor.process_file_async("data.json"):
    # Process each item as it streams
    pass
```

### 4. Security Components
```python
from ai_catalyst import (
    SecureConfigManager,  # AES-256 encryption
    APIKeyVault,         # Secure key storage with rotation
    RateLimiter,         # Token bucket algorithm
    AuditLogger          # Compliance logging
)

# Setup secure environment
config = SecureConfigManager()
key_vault = APIKeyVault()
rate_limiter = RateLimiter()
audit_logger = AuditLogger()
```

### 5. Resilience Patterns
```python
from ai_catalyst import (
    RetryHandler,    # Exponential backoff
    CircuitBreaker,  # Fault tolerance
    HealthChecker    # Service monitoring
)
```

## Key Architecture Principles

### Async-First Design
- All operations are async by default for 3-10x performance improvement
- Sync wrappers available for backward compatibility
- Use `await` with all async methods

### Security Model
- Zero-trust: All operations logged and rate-limited
- Encryption: Sensitive data encrypted at rest
- API keys managed through secure vault with rotation

### Performance Optimizations
- Concurrent processing with semaphore control
- Streaming file processing (non-blocking)
- Circuit breakers for automatic failure recovery
- Connection pooling for database operations

## Common Usage Patterns

### Basic AI Pipeline
```python
import asyncio
from ai_catalyst import LLMProvider, PIIProcessor, FileProcessor

async def process_data():
    # Initialize components
    llm = LLMProvider()
    pii = PIIProcessor()
    processor = FileProcessor()
    
    # Process files with PII scrubbing and LLM analysis
    async for item in processor.process_file_async("input.json"):
        clean_data = await pii.scrub_text_async(item['text'])
        analysis = await llm.generate_async(f"Analyze: {clean_data}")
        print(f"Result: {analysis['content']}")

asyncio.run(process_data())
```

### Production Setup with Full Security
```python
from ai_catalyst import *

# Setup security stack
key_vault = APIKeyVault()
key_vault.store_key('openai', 'your-api-key')

config = SecureConfigManager()
rate_limiter = RateLimiter()
audit_logger = AuditLogger(log_file='audit.log')

# Initialize with security
llm = LLMProvider(
    key_vault=key_vault,
    rate_limiter=rate_limiter,
    audit_logger=audit_logger
)
```

## Environment Variables
```bash
# Required for LLM providers
export OPENAI_API_KEY="your-openai-key"
export ANTHROPIC_API_KEY="your-anthropic-key"

# Security encryption
export AI_CATALYST_MASTER_KEY="your-encryption-key"
```

## Configuration File (config.yaml)
```yaml
llm:
  timeout: 30
  model: "gpt-4"
  
security:
  rate_limits:
    openai: "paid"  # or "free"
  audit_log: "audit.log"
  
processing:
  batch_size: 100
  max_concurrency: 10
```

## Development Guidelines

### When to Use AI_Catalyst
- ✅ Any LLM/AI operations (use LLMProvider)
- ✅ Processing user data (use PIIProcessor for privacy)
- ✅ File processing operations (use FileProcessor for performance)
- ✅ Production deployments (use security components)
- ✅ High-throughput scenarios (async components provide 3-10x speedup)

### Best Practices
- Always use async methods for better performance
- Enable audit logging in production environments
- Use rate limiting to prevent API quota exhaustion
- Implement circuit breakers for external service calls
- Store API keys in the secure vault, not in code

### Error Handling
All components include built-in retry logic and circuit breakers. Handle exceptions gracefully:

```python
try:
    result = await llm.generate_async(prompt)
except Exception as e:
    logger.error(f"LLM generation failed: {e}")
    # Fallback logic here
```

## Performance Expectations
- LLM failover: 3x faster (45s → 15s)
- Batch PII processing: 5x faster through concurrency
- File processing: Non-blocking streaming vs blocking reads
- Rate limiting: Sub-millisecond overhead

## Support & Documentation
- GitHub: https://github.com/ericmedlock/AI_Catalyst
- Issues: Report bugs and feature requests
- Security: Report security issues privately

---
*This context file helps AWS Q understand how to properly use AI_Catalyst components in your project.*