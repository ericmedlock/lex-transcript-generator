#!/usr/bin/env python3
"""
Test Runner Entry Point
Launch the GUI test runner or run tests from command line.
"""

import sys
import argparse
import asyncio
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

def run_gui():
    """Launch the GUI test runner"""
    try:
        import tkinter as tk
        from gui.test_runner_gui import TestRunnerGUI
        
        root = tk.Tk()
        app = TestRunnerGUI(root)
        root.mainloop()
        
    except ImportError as e:
        print(f"GUI not available: {e}")
        print("Please install tkinter or run tests from command line with --cli")
        return 1
    except Exception as e:
        print(f"GUI error: {e}")
        return 1
    
    return 0

async def run_cli(args):
    """Run tests from command line"""
    from test_framework import test_runner
    
    # Import test modules
    import importlib
    test_modules = [
        "core.test_config_manager",
        "core.test_database",
        "data.test_pii_processor", 
        "integration.test_ai_catalyst"
    ]
    
    print("Loading test modules...")
    for module_name in test_modules:
        try:
            importlib.import_module(module_name)
            print(f"[OK] Loaded {module_name}")
        except Exception as e:
            print(f"[FAIL] Failed to load {module_name}: {e}")
    
    print(f"\nFound {len(test_runner.get_all_tests())} tests in {len(test_runner.test_suites)} suites")
    
    # Run tests based on arguments
    if args.test_id:
        print(f"\nRunning single test: {args.test_id}")
        try:
            result = await test_runner.run_test(args.test_id)
            print(f"Result: {result.status.value} ({result.duration:.2f}s)")
            if result.error_message:
                print(f"Error: {result.error_message}")
            return 0 if result.status.value == "passed" else 1
        except Exception as e:
            print(f"Error running test: {e}")
            return 1
    
    elif args.suite:
        print(f"\nRunning test suite: {args.suite}")
        try:
            results = await test_runner.run_suite(args.suite)
            passed = sum(1 for r in results if r.status.value == "passed")
            total = len(results)
            print(f"\nSuite Results: {passed}/{total} tests passed")
            
            if args.verbose:
                for result in results:
                    status_symbol = "[PASS]" if result.status.value == "passed" else "[FAIL]"
                    print(f"  {status_symbol} {result.name} ({result.duration:.2f}s)")
                    if result.error_message and args.verbose:
                        print(f"    Error: {result.error_message}")
            
            return 0 if passed == total else 1
        except Exception as e:
            print(f"Error running suite: {e}")
            return 1
    
    else:
        print("\nRunning all tests...")
        try:
            all_results = await test_runner.run_all()
            
            total_passed = 0
            total_tests = 0
            
            for suite_name, results in all_results.items():
                passed = sum(1 for r in results if r.status.value == "passed")
                total = len(results)
                total_passed += passed
                total_tests += total
                
                print(f"\n{suite_name}: {passed}/{total} tests passed")
                
                if args.verbose:
                    for result in results:
                        status_symbol = "[PASS]" if result.status.value == "passed" else "[FAIL]"
                        print(f"  {status_symbol} {result.name} ({result.duration:.2f}s)")
                        if result.error_message and args.verbose:
                            print(f"    Error: {result.error_message}")
            
            print(f"\nOverall Results: {total_passed}/{total_tests} tests passed")
            
            # Export results if requested
            if args.export:
                export_path = Path(args.export)
                test_runner.export_results(export_path)
                print(f"Results exported to: {export_path}")
            
            return 0 if total_passed == total_tests else 1
            
        except Exception as e:
            print(f"Error running tests: {e}")
            return 1

def list_tests():
    """List all available tests"""
    from test_framework import test_runner
    
    # Import test modules
    import importlib
    test_modules = [
        "core.test_config_manager",
        "core.test_database", 
        "data.test_pii_processor",
        "integration.test_ai_catalyst"
    ]
    
    for module_name in test_modules:
        try:
            importlib.import_module(module_name)
        except Exception as e:
            print(f"Warning: Failed to load {module_name}: {e}")
    
    print("Available Test Suites:")
    print("=" * 50)
    
    for suite_name, suite in test_runner.test_suites.items():
        print(f"\nSuite: {suite_name}")
        print(f"Description: {suite.description}")
        print(f"Tests ({len(suite.tests)}):")
        
        for test in suite.tests:
            print(f"  {test.test_id}: {test.name}")
            print(f"    {test.description}")
    
    print(f"\nTotal: {len(test_runner.get_all_tests())} tests in {len(test_runner.test_suites)} suites")

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="LLM Transcript Platform Test Runner")
    parser.add_argument("--cli", action="store_true", help="Run in command line mode")
    parser.add_argument("--list", action="store_true", help="List all available tests")
    parser.add_argument("--test-id", help="Run a specific test by ID")
    parser.add_argument("--suite", help="Run a specific test suite")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--export", help="Export results to JSON file")
    
    args = parser.parse_args()
    
    if args.list:
        list_tests()
        return 0
    
    if args.cli or args.test_id or args.suite:
        return asyncio.run(run_cli(args))
    else:
        return run_gui()

if __name__ == "__main__":
    sys.exit(main())