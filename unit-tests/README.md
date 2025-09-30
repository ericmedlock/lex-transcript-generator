# Unit Tests - LLM Transcript Data Generation Platform

## Overview

This comprehensive testing suite provides verification and regression testing for the distributed transcript intelligence platform. The test framework includes both GUI and command-line interfaces for flexible test execution.

## Quick Start

### GUI Mode (Recommended)
```bash
cd unit-tests
python run_tests.py
```

### Command Line Mode
```bash
# List all available tests
python run_tests.py --list

# Run all tests
python run_tests.py --cli

# Run specific test suite
python run_tests.py --cli --suite config_manager

# Run single test
python run_tests.py --cli --test-id config_001

# Run with verbose output and export results
python run_tests.py --cli --verbose --export results.json
```

## Test Structure

```
unit-tests/
├── core/                   # Core component tests
│   ├── test_config_manager.py
│   ├── test_database.py
│   └── test_conversation_grader.py
├── data/                   # Data processing tests
│   ├── test_pii_processor.py
│   ├── test_lex_validator.py
│   └── test_file_processor.py
├── nodes/                  # Node management tests
│   ├── test_generation_node.py
│   └── test_orchestrator.py
├── integration/            # End-to-end tests
│   ├── test_ai_catalyst.py
│   └── test_full_pipeline.py
├── performance/            # Performance tests
│   ├── test_load_performance.py
│   └── test_stress_limits.py
├── gui/                    # GUI test runner
│   └── test_runner_gui.py
├── test_framework.py       # Core test framework
├── run_tests.py           # Main entry point
├── TEST_PLAN.md           # Detailed test documentation
└── README.md              # This file
```

## Test Categories

### Core Component Tests
- **Configuration Manager**: YAML loading, database overrides, nested access
- **Database Operations**: Connectivity, schema management, transactions
- **Conversation Grading**: AI-powered quality assessment
- **Deduplication**: Hash-based and semantic similarity detection

### Data Processing Tests
- **PII Processor**: Detection and scrubbing of sensitive information
- **LEX Validator**: Contact Lens format compliance
- **File Processor**: Async streaming and format detection

### Integration Tests
- **AI-Catalyst**: Framework component integration
- **Full Pipeline**: End-to-end workflow validation

### Performance Tests
- **Load Testing**: Concurrent processing validation
- **Stress Testing**: System limit determination

## GUI Features

The GUI test runner provides:

- **Test Selection**: Choose individual tests, suites, or run all
- **Real-time Monitoring**: Live test execution progress
- **Result Analysis**: Detailed success/failure reporting
- **Export/Import**: Save and load test results
- **Test Plan Access**: Direct link to documentation

### GUI Controls

- **Run All Tests**: Execute complete regression suite
- **Run Selected**: Execute highlighted test
- **Run Suite**: Execute all tests in selected suite
- **Stop**: Halt running tests
- **Export Results**: Save results to JSON file
- **Load Results**: Import previous test results

## Test Framework Features

### Async Support
- Full async/await support for modern Python testing
- Timeout handling for long-running tests
- Concurrent test execution capabilities

### Result Tracking
- Comprehensive test result metadata
- Duration tracking and performance metrics
- Error message capture and stack traces
- Test status tracking (Pending, Running, Passed, Failed, Error, Skipped)

### Extensibility
- Easy test case registration
- Suite-based organization
- Setup/teardown support
- Custom assertion library

## Writing New Tests

### Basic Test Structure
```python
from unit_tests.test_framework import TestCase, TestSuite, TestAssertions, test_runner

def test_my_feature():
    """Test description"""
    # Test implementation
    TestAssertions.assert_equals(actual, expected, "Error message")

# Register test
test_case = TestCase(
    test_id="my_001",
    name="My Feature Test",
    description="Detailed test description",
    test_func=test_my_feature,
    category="core"
)

suite = TestSuite(
    name="my_suite",
    description="My Test Suite",
    tests=[test_case]
)

test_runner.register_suite(suite)
```

### Async Test Example
```python
async def test_async_feature():
    """Test async functionality"""
    result = await some_async_function()
    TestAssertions.assert_not_none(result, "Should return result")

test_case = TestCase(
    test_id="async_001",
    name="Async Feature Test", 
    description="Test async functionality",
    test_func=test_async_feature,
    category="integration"
)
```

### Test Suite with Setup/Teardown
```python
class TestMyComponent:
    def setup(self):
        """Setup test environment"""
        self.component = MyComponent()
    
    def teardown(self):
        """Cleanup after tests"""
        self.component.cleanup()
    
    def test_feature(self):
        """Test implementation"""
        result = self.component.do_something()
        TestAssertions.assert_true(result, "Should succeed")

test_component = TestMyComponent()

suite = TestSuite(
    name="my_component",
    description="My Component Tests",
    tests=[...],
    setup_func=test_component.setup,
    teardown_func=test_component.teardown
)
```

## Available Assertions

```python
TestAssertions.assert_equals(actual, expected, message)
TestAssertions.assert_true(condition, message)
TestAssertions.assert_false(condition, message)
TestAssertions.assert_not_none(value, message)
TestAssertions.assert_in(item, container, message)
TestAssertions.assert_raises(exception_type, func, *args, **kwargs)
```

## Performance Benchmarks

### Expected Performance
- **Configuration Loading**: < 100ms
- **Database Connection**: < 500ms
- **PII Scrubbing**: < 1s for 1000 words
- **File Processing**: > 1MB/s throughput
- **Test Suite Execution**: < 5 minutes full regression

### Performance Test Categories
- **Unit Test Performance**: Individual test execution speed
- **Integration Performance**: End-to-end workflow timing
- **Load Testing**: Concurrent operation handling
- **Memory Usage**: Resource consumption monitoring

## Continuous Integration

### Automated Testing
```bash
# Quick smoke test (5 minutes)
python run_tests.py --cli --suite core

# Full regression (30-60 minutes)  
python run_tests.py --cli --export ci_results.json
```

### Test Result Analysis
- **Pass Rate**: Target 95%+ for core components
- **Performance**: No regression > 20% from baseline
- **Coverage**: All critical paths tested
- **Reliability**: Consistent results across runs

## Troubleshooting

### Common Issues

**Import Errors**: Ensure project root is in Python path
```bash
export PYTHONPATH="${PYTHONPATH}:/path/to/LLM-Transcript-Data-Gen"
```

**GUI Not Available**: Install tkinter or use CLI mode
```bash
python run_tests.py --cli
```

**Test Timeouts**: Increase timeout for slow tests
```python
TestCase(..., timeout=60)  # 60 second timeout
```

**Database Connection**: Ensure test database is available
```bash
# Check database connectivity
python -c "from src.core.database import DatabaseManager; print('DB OK')"
```

### Debug Mode
```bash
# Run with Python debug mode
python -u run_tests.py --cli --verbose
```

## Contributing

### Adding New Tests
1. Create test file in appropriate category directory
2. Follow naming convention: `test_component_name.py`
3. Import and register test suite
4. Update TEST_PLAN.md with test documentation
5. Verify tests pass in both GUI and CLI modes

### Test Quality Guidelines
- Each test should be independent and isolated
- Use descriptive test names and error messages
- Include both positive and negative test cases
- Test edge cases and error conditions
- Maintain reasonable test execution time (< 30s per test)

## Support

For issues with the test framework:
1. Check TEST_PLAN.md for detailed test documentation
2. Review test logs for specific error messages
3. Verify all dependencies are installed
4. Ensure proper Python path configuration

## Version History

- **v1.0.0**: Initial comprehensive test suite with GUI
- Core component tests implemented
- AI-Catalyst integration tests
- Performance benchmarking framework
- GUI test runner with real-time monitoring