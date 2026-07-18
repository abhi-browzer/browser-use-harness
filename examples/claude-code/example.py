#!/usr/bin/env python3
"""Basic browser-harness example demonstrating browser automation.

This script:
1. Connects to your running Chrome instance via CDP
2. Navigates to a webpage
3. Retrieves page information
4. Takes a screenshot

Prerequisites:
- Chrome with remote debugging enabled (chrome://inspect/#remote-debugging)
- browser-harness installed (pip install browser-harness)
"""

import os
import subprocess
import sys
from pathlib import Path


def run_browser_harness_command(python_code: str) -> str:
    """Execute Python code via browser-harness CLI.
    
    Args:
        python_code: Python code to execute in browser-harness context
        
    Returns:
        Output from the command
    """
    try:
        result = subprocess.run(
            ["browser-harness"],
            input=python_code,
            text=True,
            capture_output=True,
            check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error executing browser-harness: {e.stderr}", file=sys.stderr)
        raise
    except FileNotFoundError:
        print(
            "Error: browser-harness command not found.\n"
            "Install with: pip install browser-harness",
            file=sys.stderr
        )
        raise


def main():
    """Main automation workflow."""
    print("=" * 60)
    print("Browser Harness + Claude Code Example")
    print("=" * 60)
    print()
    
    # Check for optional environment variables
    cdp_url = os.getenv("BU_CDP_URL")
    domain_skills = os.getenv("BH_DOMAIN_SKILLS")
    
    if cdp_url:
        print(f"Using custom CDP URL: {cdp_url}")
    else:
        print("Using default CDP URL: ws://localhost:9222")
    
    if domain_skills:
        print("Domain skills enabled")
    
    print()
    print("Step 1: Get page info")
    print("-" * 60)
    
    # Get current page information
    page_info_code = "print(page_info())"
    try:
        output = run_browser_harness_command(page_info_code)
        print(output)
    except Exception as e:
        print(f"Failed to get page info. Is Chrome running with remote debugging?")
        print(f"Error: {e}")
        return 1
    
    print()
    print("Step 2: Navigate to example.com")
    print("-" * 60)
    
    # Navigate to a test page
    navigate_code = """
navigate('https://example.com')
print('Navigation complete')
print(page_info())
"""
    output = run_browser_harness_command(navigate_code)
    print(output)
    
    print()
    print("Step 3: Take screenshot")
    print("-" * 60)
    
    # Take a screenshot
    screenshot_path = Path("screenshot.png").absolute()
    screenshot_code = f"""
screenshot_path = r'{screenshot_path}'
take_screenshot(screenshot_path)
print(f'Screenshot saved to: {{screenshot_path}}')
"""
    output = run_browser_harness_command(screenshot_code)
    print(output)
    
    print()
    print("=" * 60)
    print("Example complete!")
    print()
    print("Next steps:")
    print("1. Paste the setup prompt into Claude Code (see README.md)")
    print("2. Ask Claude to perform browser tasks")
    print("3. The agent will write helpers as needed")
    print("=" * 60)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
