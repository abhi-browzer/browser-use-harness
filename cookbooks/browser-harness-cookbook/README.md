**Browser Harness is a thin CDP harness that connects LLMs directly to your real browser.** Unlike traditional automation frameworks, the agent writes missing helpers during execution—the harness improves itself every run.

This cookbook covers core Browser Harness patterns: connecting to Chrome, inspecting pages, writing custom helpers, creating reusable domain skills, and deploying with Browser Use Cloud. Every recipe uses the real APIs from the `browser-harness` package and the agent workspace architecture.

## How to Connect Browser Harness to Your Local Chrome

You need to establish a CDP connection to your running Chrome browser so Browser Harness can control it. This is the first step for any browser automation task.

**Prerequisites**
- Chrome or Chromium installed
- Python 3.12+
- browser-harness installed: pip install browser-harness

```bash
# 1. Enable remote debugging in Chrome
# Open chrome://inspect/#remote-debugging
# Check "Discover network targets" checkbox
# Allow the connection when the Chrome 144+ popup appears

# 2. Verify connection with a simple command
browser-harness <<'PY'
print(page_info())
PY
```

Browser Harness attaches to Chrome's CDP endpoint automatically. When you run `browser-harness` with Python code, it:

1. Looks for a running Chrome instance with remote debugging enabled
2. Connects via WebSocket to the CDP endpoint
3. Executes your code in the context of the active browser tab

The `page_info()` helper returns metadata about the current page (URL, title, etc.). No need to specify ports or endpoints—Browser Harness discovers the connection automatically.

For manual port control or isolated automation, launch Chrome with `--remote-debugging-port=9222` and set `BU_CDP_URL=ws://localhost:9222`.

**Expected output**

```
{
  "url": "https://example.com",
  "title": "Example Domain",
  "readyState": "complete"
}
```

**Gotchas**
- Chrome must have remote debugging enabled before running browser-harness—open chrome://inspect/#remote-debugging and check the box
- Chrome 144+ shows an "Allow remote debugging?" popup per attach—click Allow or the connection fails
- If multiple Chrome profiles are running, Browser Harness connects to the first one it finds; close others or specify BU_CDP_URL explicitly

## How to Write and Execute Custom Helper Functions

The agent encounters a task (like uploading a file or parsing a table) that needs custom logic not in the base harness. You need to add a helper function that persists across runs.

**Prerequisites**
- browser-harness connected to Chrome
- Agent workspace directory exists (created automatically on first run)

```python
# agent_helpers.py lives in:
# ${XDG_CONFIG_HOME:-~/.config}/browser-harness/agent-workspace/agent_helpers.py

# Add a new helper (agent does this automatically, but you can edit manually)
def upload_file_to_input(file_path: str, input_selector: str):
    """Upload a local file to a file input element."""
    import json
    element = document.querySelector(input_selector)
    if not element:
        raise ValueError(f"No element found for selector: {input_selector}")
    
    # Use CDP to set files on the input
    result = cdp_call('DOM.setFileInputFiles', {
        'files': [file_path],
        'nodeId': get_node_id(element)
    })
    return result

# Now use it in your automation script:
browser-harness <<'PY'
from agent_helpers import upload_file_to_input

upload_file_to_input(
    '/path/to/document.pdf',
    'input[type="file"]'
)
print("File uploaded successfully")
PY
```

Browser Harness uses an **agent workspace** at `${XDG_CONFIG_HOME:-~/.config}/browser-harness/agent-workspace/` where the agent writes helper code.

The `agent_helpers.py` file is automatically imported and available in every `browser-harness` execution. When the agent discovers it needs a new capability:

1. It writes the helper function to `agent_helpers.py`
2. The helper is immediately available for import
3. Future runs reuse the helper—no re-learning needed

Helpers can call CDP methods directly via `cdp_call()`, manipulate the DOM via JavaScript injection, or wrap complex multi-step flows. The harness improves itself incrementally.

You can also manually edit `agent_helpers.py` to refine logic, add type hints, or optimize performance. The agent treats it as a living codebase.

**Expected output**

```
File uploaded successfully
```

**Gotchas**
- agent_helpers.py must use valid Python syntax or the next browser-harness run will fail with a syntax error
- Helpers run in the browser's JavaScript context for DOM operations but Python context for logic—be clear about which environment you're targeting
- If a helper has a bug, the agent usually fixes it on the next run by editing agent_helpers.py; you can also fix it manually

## How to Create and Use Domain Skills for Site-Specific Automation

You repeatedly automate tasks on a specific site (LinkedIn, Amazon, GitHub) and want to capture selectors, flows, and edge cases so the agent doesn't have to rediscover them every time.

**Prerequisites**
- browser-harness connected
- Domain skills enabled: export BH_DOMAIN_SKILLS=1

```bash
# Enable domain skills
export BH_DOMAIN_SKILLS=1

# Run a task on LinkedIn (example)
browser-harness <<'PY'
# The agent navigates LinkedIn and performs a task.
# When it figures out non-obvious selectors or flows,
# it writes them to:
# agent-workspace/domain-skills/linkedin/selectors.json
# agent-workspace/domain-skills/linkedin/flows.md

from pathlib import Path
import json

# Check if a skill exists
skill_path = Path.home() / '.config/browser-harness/agent-workspace/domain-skills/linkedin'
if skill_path.exists():
    selectors = json.loads((skill_path / 'selectors.json').read_text())
    print(f"Loaded {len(selectors)} LinkedIn selectors")
    print(selectors)
else:
    print("No LinkedIn skill found yet—agent will create one during first run")
PY
```

**Domain skills** are site-specific knowledge files stored under `agent-workspace/domain-skills/<site>/`. When `BH_DOMAIN_SKILLS=1` is set, the agent:

1. Checks if a skill exists for the current domain
2. Loads selectors, flows, and edge cases if found
3. Writes new discoveries back to the skill directory during execution

Skills typically include:
- `selectors.json` — CSS/XPath selectors for key elements (login button, search bar, etc.)
- `flows.md` — Multi-step procedures (how to post, how to message, etc.)
- `edge_cases.md` — Anti-patterns, dynamic content handling, etc.

**Skills are agent-generated, not hand-written.** Just run your task normally—the agent files the skill itself when it learns something non-obvious. Over time, the harness becomes expert on the sites you use most.

To contribute a skill to this repo, run your task, then copy the generated `domain-skills/<site>/` folder into the repo's `agent-workspace/domain-skills/` and open a PR.

**Expected output**

```
Loaded 8 LinkedIn selectors
{
  "login_email_input": "#username",
  "login_password_input": "#password",
  "login_submit_button": "button[type='submit']",
  "feed_post_button": "button[aria-label='Start a post']",
  ...
}
```

**Gotchas**
- Domain skills only activate when BH_DOMAIN_SKILLS=1 is set; without it, the agent operates from scratch every time
- Skills are site-specific and may break if the site redesigns—the agent will update the skill on the next run if selectors fail
- Don't hand-author skill files; agent-generated ones capture what actually works in practice, including edge cases you'd miss

## How to Use Browser Use Cloud for Remote or Headless Automation

You need stealth browsers, proxies, captcha solving, or want to run browser tasks in CI/CD without managing Chrome yourself. Browser Use Cloud provides free remote browsers.

**Prerequisites**
- Browser Use Cloud API key (get one at cloud.browser-use.com/new-api-key)
- browser-harness installed

```bash
# 1. Set your Browser Use Cloud API key
export BROWSER_USE_API_KEY='your_api_key_here'

# 2. Run browser-harness—it automatically connects to a cloud browser
browser-harness <<'PY'
import os

# The harness connects to a Browser Use Cloud instance automatically
# when BROWSER_USE_API_KEY is set
print(page_info())

# Navigate and perform tasks as usual
cdp_call('Page.navigate', {'url': 'https://example.com'})
wait_for_load()
print(f"Connected to cloud browser at: {os.getenv('BU_CDP_URL', 'auto-detected')}")
PY
```

Browser Use Cloud provides **managed Chrome instances** with features like:

- Residential proxies
- Automatic captcha solving
- Stealth fingerprinting
- Sub-agents (multiple isolated browser contexts)
- No local Chrome required

When `BROWSER_USE_API_KEY` is set, Browser Harness automatically provisions a cloud browser and connects to it instead of your local Chrome. The API is identical—your scripts run unchanged.

**Free tier includes:**
- 3 concurrent browsers
- Proxies and captcha solving
- No credit card required

For CI/CD or production deployments, this removes the need to manage Chrome binaries, versions, and driver updates. Just set the API key and run your scripts.

You can also manually control the cloud browser by setting `BU_CDP_URL` to a specific cloud instance endpoint if you need multi-browser orchestration.

**Expected output**

```
{
  "url": "https://example.com",
  "title": "Example Domain",
  "readyState": "complete"
}
Connected to cloud browser at: auto-detected
```

**Gotchas**
- Cloud browsers are ephemeral—sessions end when your script exits; use persistent storage if you need state across runs
- The free tier limits concurrent browsers to 3; additional browsers queue until a slot frees up
- Cloud browsers may have different IP geolocation than your local machine; set proxy regions if you need specific locales

## How to Inspect and Debug Browser State During Execution

Your automation script isn't working as expected, and you need to see the current page structure, console logs, or network activity to diagnose the issue.

**Prerequisites**
- browser-harness connected to Chrome
- Active browser tab open

```python
browser-harness <<'PY'
import json

# Get current page info
info = page_info()
print("=== Page Info ===")
print(json.dumps(info, indent=2))

# Capture a screenshot for visual debugging
screenshot_data = cdp_call('Page.captureScreenshot', {'format': 'png'})
with open('/tmp/debug_screenshot.png', 'wb') as f:
    import base64
    f.write(base64.b64decode(screenshot_data['data']))
print("Screenshot saved to /tmp/debug_screenshot.png")

# Get the current DOM structure (simplified)
dom_root = cdp_call('DOM.getDocument', {})
print("\n=== DOM Root ===")
print(json.dumps(dom_root['root'], indent=2))

# Execute JavaScript to inspect state
result = cdp_call('Runtime.evaluate', {
    'expression': 'document.querySelectorAll("button").length',
    'returnByValue': True
})
print(f"\nNumber of buttons on page: {result['result']['value']}")

# Get console messages (if you've enabled console event listeners)
print("\n=== Debug complete ===")
PY
```

Browser Harness exposes raw CDP methods via `cdp_call()`, giving you full access to Chrome DevTools Protocol features:

- **`page_info()`** — Quick page metadata (URL, title, ready state)
- **`Page.captureScreenshot`** — Visual debugging; save screenshots at any point
- **`DOM.getDocument`** — Inspect the full DOM tree structure
- **`Runtime.evaluate`** — Execute arbitrary JavaScript and get results back

For deep debugging:

1. Use `cdp_call('Network.enable', {})` to capture network traffic
2. Use `cdp_call('Console.enable', {})` to get console logs
3. Use `cdp_call('Debugger.enable', {})` to set breakpoints in page JavaScript

The harness is a thin layer over CDP—anything you can do in DevTools, you can script here. When helpers fail, drop into CDP calls to see exactly what the browser is doing.

For interactive debugging, run `browser-harness` with a Python REPL or use the agent's workspace to add print statements in `agent_helpers.py`.

**Expected output**

```
=== Page Info ===
{
  "url": "https://example.com",
  "title": "Example Domain",
  "readyState": "complete"
}
Screenshot saved to /tmp/debug_screenshot.png

=== DOM Root ===
{
  "nodeId": 1,
  "nodeType": 9,
  "nodeName": "#document",
  ...
}

Number of buttons on page: 3

=== Debug complete ===
```

**Gotchas**
- cdp_call() is synchronous and blocks until the CDP method completes; slow operations (like large DOM queries) can hang your script
- Screenshot data is base64-encoded; decode it before writing to a file or it will be corrupted
- DOM node IDs are ephemeral—they change when the page updates; re-query nodes if your script does navigation or waits

## How to Register and Use the Browser Harness Skill in Coding Agents

You want to integrate Browser Harness into an LLM coding agent (Claude Code, Codex, etc.) so the agent can autonomously perform browser tasks as part of its workflow.

**Prerequisites**
- browser-harness installed
- A coding agent that supports custom skills/tools (Claude Code, Codex, etc.)

```bash
# 1. Register the Browser Harness skill with your agent
browser-harness skill

# This outputs a skill definition you paste into your agent's configuration.
# The skill definition includes:
# - Name: browser_harness
# - Description: Connect to Chrome via CDP and perform browser automation
# - Usage examples and parameters

# 2. Example agent prompt after skill registration:
# "Navigate to GitHub, search for 'browser-harness', and star the repo."

# The agent will automatically:
# - Call the browser_harness skill
# - Generate Python code using Browser Harness helpers
# - Execute the code via browser-harness
# - Return results

# 3. For first-time setup, use this prompt with your agent:
# "Install or upgrade browser-harness to the latest stable version with uv
#  using Python 3.12, register the skill from `browser-harness skill`,
#  and connect it to my browser. Follow
#  https://github.com/browser-use/browser-harness/blob/main/install.md
#  if setup or connection fails."
```

The `browser-harness skill` command outputs a **skill definition** in your agent's expected format (MCP, tool schema, etc.). Once registered, the agent can:

1. Invoke Browser Harness as a first-class tool
2. Generate Python code using helpers like `page_info()`, `cdp_call()`, domain skills, etc.
3. Execute the code and get results back

The skill definition includes:
- **Parameters:** Optional CDP URL, timeout settings, domain skill flags
- **Usage examples:** Navigation, form filling, data extraction patterns
- **Error handling:** Common failure modes and retry strategies

**Agent workflow example:**

```
User: "Find the top 3 results for 'AI agents' on Hacker News"
  ↓
Agent: Invokes browser_harness skill with Python:
  navigate('https://news.ycombinator.com')
  search('AI agents')
  results = extract_top_results(3)
  ↓
Agent: Returns results to user
```

The agent can also **write new helpers** when it encounters gaps. If it needs to handle pagination or parse a table format, it adds the helper to `agent_helpers.py` and reuses it in future tasks.

See `agent-workspace/domain-skills/` in the repo for example task patterns the agent can learn from.

**Expected output**

```
# Browser Harness Skill Definition (example MCP format)

name: browser_harness
description: |
  Connect to Chrome via CDP and perform browser automation.
  Use for tasks requiring real browser interaction.
parameters:
  - name: code
    type: string
    description: Python code using Browser Harness helpers
  - name: cdp_url
    type: string
    optional: true
    description: Override CDP endpoint (default: auto-detect)
usage_examples:
  - Navigate and extract: page_info()
  - Fill form: cdp_call('DOM.setAttributeValue', ...)
  - Screenshot: cdp_call('Page.captureScreenshot', ...)
```

**Gotchas**
- The agent must have Python 3.12+ available; older Python versions may lack required features
- If the agent generates invalid Python, browser-harness fails with a SyntaxError; the agent usually fixes it on retry
- Agent-written helpers persist in agent_helpers.py—review them periodically to ensure quality and remove obsolete ones

## FAQ

### Does Browser Harness require Chrome to be running, or can it launch Chrome itself?

Browser Harness attaches to an already-running Chrome instance by default. For isolated automation, launch Chrome yourself with `--remote-debugging-port=9222` and set `BU_CDP_URL=ws://localhost:9222`, or use Browser Use Cloud (which launches managed Chrome instances automatically).

### What's the difference between agent_helpers.py and domain skills?

agent_helpers.py contains general-purpose helper functions (upload files, parse tables, etc.) used across any site. Domain skills are site-specific knowledge (LinkedIn selectors, GitHub flows, etc.) stored in domain-skills/<site>/ and only loaded when BH_DOMAIN_SKILLS=1 is set. Both improve automatically as the agent runs.

### Can I use Browser Harness in CI/CD without a display server?

Yes. Use Browser Use Cloud by setting BROWSER_USE_API_KEY—no local Chrome or Xvfb needed. Alternatively, run Chrome headless with `--headless=new --remote-debugging-port=9222` and connect via BU_CDP_URL.

### How do I contribute a domain skill to the Browser Harness repo?

Run your task with BH_DOMAIN_SKILLS=1 enabled. The agent will create domain-skills/<site>/ with selectors, flows, and edge cases. Copy that folder into the repo's agent-workspace/domain-skills/ and open a PR. Do not hand-author skill files—only contribute agent-generated ones.

### What happens if a helper function in agent_helpers.py has a bug?

The agent usually fixes it on the next run by editing agent_helpers.py. You can also manually edit the file to fix the bug yourself. Browser Harness treats the agent workspace as a living codebase that improves over time.

## Key takeaways

- Browser Harness is a thin CDP layer connecting LLMs directly to Chrome—the agent writes missing helpers during execution, and the harness improves itself every run.
- Use agent_helpers.py for general-purpose helper functions and domain-skills/ for site-specific knowledge; both are agent-editable and persist across runs.
- Enable domain skills with BH_DOMAIN_SKILLS=1 to load and contribute reusable site-specific automation patterns—skills are always agent-generated, never hand-authored.
- Browser Use Cloud provides free managed Chrome instances with proxies, captcha solving, and stealth—just set BROWSER_USE_API_KEY to eliminate local Chrome dependencies.
- Register the Browser Harness skill with coding agents via `browser-harness skill` to enable autonomous browser task execution as part of agent workflows.
- Debug with raw CDP calls via cdp_call()—full DevTools Protocol access means you can inspect, screenshot, and control the browser at any level of detail.