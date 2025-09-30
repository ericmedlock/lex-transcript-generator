#!/usr/bin/env python3
"""
Test Framework - Core testing infrastructure for the LLM Transcript Platform
"""

import asyncio
import json
import time
import traceback
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any
import sys
import os

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

class TestStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"

@dataclass
class TestResult:
    test_id: str
    name: str
    description: str
    status: TestStatus
    duration: float = 0.0
    error_message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    timestamp: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

@dataclass
class TestSuite:
    name: str
    description: str
    tests: List['TestCase']
    setup_func: Optional[Callable] = None
    teardown_func: Optional[Callable] = None

class TestCase:
    def __init__(self, test_id: str, name: str, description: str, 
                 test_func: Callable, category: str = "general",
                 prerequisites: List[str] = None, timeout: int = 30):
        self.test_id = test_id
        self.name = name
        self.description = description
        self.test_func = test_func
        self.category = category
        self.prerequisites = prerequisites or []
        self.timeout = timeout
        self.result: Optional[TestResult] = None
    
    async def run(self) -> TestResult:
        """Execute the test case and return results"""
        start_time = time.time()
        
        self.result = TestResult(
            test_id=self.test_id,
            name=self.name,
            description=self.description,
            status=TestStatus.RUNNING
        )
        
        try:
            # Run test with timeout
            if asyncio.iscoroutinefunction(self.test_func):
                await asyncio.wait_for(self.test_func(), timeout=self.timeout)
            else:
                self.test_func()
            
            self.result.status = TestStatus.PASSED
            
        except asyncio.TimeoutError:
            self.result.status = TestStatus.ERROR
            self.result.error_message = f"Test timed out after {self.timeout} seconds"
            
        except AssertionError as e:
            self.result.status = TestStatus.FAILED
            self.result.error_message = str(e)
            
        except Exception as e:
            self.result.status = TestStatus.ERROR
            self.result.error_message = f"{type(e).__name__}: {str(e)}"
            self.result.details = {"traceback": traceback.format_exc()}
        
        finally:
            self.result.duration = time.time() - start_time
        
        return self.result

class TestRunner:
    def __init__(self):
        self.test_suites: Dict[str, TestSuite] = {}
        self.results: List[TestResult] = []
        self.callbacks: List[Callable] = []
    
    def register_suite(self, suite: TestSuite):
        """Register a test suite"""
        self.test_suites[suite.name] = suite
    
    def add_callback(self, callback: Callable):
        """Add callback for test progress updates"""
        self.callbacks.append(callback)
    
    def _notify_callbacks(self, event: str, data: Any):
        """Notify all registered callbacks"""
        for callback in self.callbacks:
            try:
                callback(event, data)
            except Exception as e:
                print(f"Callback error: {e}")
    
    async def run_test(self, test_id: str) -> TestResult:
        """Run a single test by ID"""
        for suite in self.test_suites.values():
            for test in suite.tests:
                if test.test_id == test_id:
                    self._notify_callbacks("test_started", test)
                    result = await test.run()
                    self.results.append(result)
                    self._notify_callbacks("test_completed", result)
                    return result
        
        raise ValueError(f"Test {test_id} not found")
    
    async def run_suite(self, suite_name: str) -> List[TestResult]:
        """Run all tests in a suite"""
        if suite_name not in self.test_suites:
            raise ValueError(f"Suite {suite_name} not found")
        
        suite = self.test_suites[suite_name]
        suite_results = []
        
        self._notify_callbacks("suite_started", suite)
        
        # Run setup if provided
        if suite.setup_func:
            try:
                if asyncio.iscoroutinefunction(suite.setup_func):
                    await suite.setup_func()
                else:
                    suite.setup_func()
            except Exception as e:
                self._notify_callbacks("suite_setup_failed", str(e))
                return []
        
        # Run all tests in suite
        for test in suite.tests:
            result = await self.run_test(test.test_id)
            suite_results.append(result)
        
        # Run teardown if provided
        if suite.teardown_func:
            try:
                if asyncio.iscoroutinefunction(suite.teardown_func):
                    await suite.teardown_func()
                else:
                    suite.teardown_func()
            except Exception as e:
                self._notify_callbacks("suite_teardown_failed", str(e))
        
        self._notify_callbacks("suite_completed", suite_results)
        return suite_results
    
    async def run_all(self) -> Dict[str, List[TestResult]]:
        """Run all registered test suites"""
        all_results = {}
        
        for suite_name in self.test_suites:
            all_results[suite_name] = await self.run_suite(suite_name)
        
        return all_results
    
    def get_test_by_id(self, test_id: str) -> Optional[TestCase]:
        """Get test case by ID"""
        for suite in self.test_suites.values():
            for test in suite.tests:
                if test.test_id == test_id:
                    return test
        return None
    
    def get_all_tests(self) -> List[TestCase]:
        """Get all registered tests"""
        all_tests = []
        for suite in self.test_suites.values():
            all_tests.extend(suite.tests)
        return all_tests
    
    def get_results_summary(self) -> Dict[str, int]:
        """Get summary of test results"""
        summary = {status.value: 0 for status in TestStatus}
        
        for result in self.results:
            summary[result.status.value] += 1
        
        return summary
    
    def export_results(self, filepath: Path):
        """Export test results to JSON"""
        results_data = {
            "timestamp": datetime.now().isoformat(),
            "summary": self.get_results_summary(),
            "results": [asdict(result) for result in self.results]
        }
        
        with open(filepath, 'w') as f:
            json.dump(results_data, f, indent=2, default=str)

# Test utilities and assertions
class TestAssertions:
    @staticmethod
    def assert_equals(actual, expected, message=""):
        if actual != expected:
            raise AssertionError(f"{message}: Expected {expected}, got {actual}")
    
    @staticmethod
    def assert_true(condition, message=""):
        if not condition:
            raise AssertionError(f"{message}: Expected True, got False")
    
    @staticmethod
    def assert_false(condition, message=""):
        if condition:
            raise AssertionError(f"{message}: Expected False, got True")
    
    @staticmethod
    def assert_not_none(value, message=""):
        if value is None:
            raise AssertionError(f"{message}: Expected non-None value")
    
    @staticmethod
    def assert_in(item, container, message=""):
        if item not in container:
            raise AssertionError(f"{message}: {item} not found in {container}")
    
    @staticmethod
    def assert_raises(exception_type, func, *args, **kwargs):
        try:
            func(*args, **kwargs)
            raise AssertionError(f"Expected {exception_type.__name__} to be raised")
        except exception_type:
            pass  # Expected exception
        except Exception as e:
            raise AssertionError(f"Expected {exception_type.__name__}, got {type(e).__name__}")

# Global test runner instance
test_runner = TestRunner()