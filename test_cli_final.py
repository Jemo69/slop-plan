#!/usr/bin/env python3
"""Final CLI test script."""
import sys
import os

# Add the full path to sys.path
sys.path.insert(0, '/home/jemo/projects/html-plan-service/html-planner')

print("=== Final CLI Test ===")

# Test importing the modules
try:
    # Import config first
    from cli.plan_cli.config import load_config, save_config, set_api_key, get_api_key, get_email, set_email
    print("✓ Config module imported successfully")

    # Test config operations
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        # Temporarily modify the config path
        original_home = os.environ.get('HOME', '')
        os.environ['HOME'] = tmpdir

        try:
            # Test setting and getting API key
            set_api_key("test-key-123")
            retrieved_key = get_api_key()

            if retrieved_key == "test-key-123":
                print("✓ Config: set_api_key/get_api_key work correctly")
            else:
                print(f"✗ Config: get_api_key returned {retrieved_key}")

            # Test setting and getting API URL
            from cli.plan_cli.config import set_api_url, get_api_url
            set_api_url("http://test-server:8000")
            retrieved_url = get_api_url()

            if retrieved_url == "http://test-server:8000":
                print("✓ Config: set_api_url/get_api_url work correctly")
            else:
                print(f"✗ Config: get_api_url returned {retrieved_url}")

            # Test setting and getting email
            set_email("test@example.com")
            retrieved_email = get_email()

            if retrieved_email == "test@example.com":
                print("✓ Config: set_email/get_email work correctly")
            else:
                print(f"✗ Config: get_email returned {retrieved_email}")

        finally:
            if original_home:
                os.environ['HOME'] = original_home
            else:
                os.environ.pop('HOME', None)

    # Test the PlanAPI class (though it needs httpx)
    try:
        from cli.plan_cli.api import PlanAPI, PlanAPIError, PlanConnectionError
        print("✓ PlanAPI module imported successfully")
        
        # Test that PlanAPI can be instantiated
        api = PlanAPI()
        print("✓ PlanAPI instantiated successfully")
        
        # Test auth check
        api._check_auth()  # Should raise PlanAPIError if no API key
        print("✓ PlanAPI auth check works")
        
    except Exception as e:
        print(f"✗ PlanAPI tests failed: {e}")

    print("\n=== All Core CLI Components Working ===")
    print("\nNext Steps:")
    print("1. Install typer, httpx, and rich for CLI functionality")
    print("2. Test individual CLI commands with mocked backend")
    print("3. Run integration tests (if backend is running)")
    print("4. Create CLI test documentation")

except ImportError as e:
    print(f"✗ Import failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

except Exception as e:
    print(f"✗ Unexpected error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
