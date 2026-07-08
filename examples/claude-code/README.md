# Browser Harness + Claude Code Example

A minimal example showing how to use **browser-harness** with **Claude Code** to automate browser tasks. The agent connects to your running Chrome via CDP and can write its own helper functions during execution.

## Prerequisites

- Python 3.12+
- Chrome or Chromium with remote debugging enabled
- Claude Code (Claude Desktop, CLI, or API with MCP support)

## Setup

1. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

2. **Enable Chrome remote debugging:**

   - Navigate to `chrome://inspect/#remote-debugging` in Chrome
   - Check "Discover network targets"
   - Click "Allow" when the per-attach popup appears (Chrome 144+)

3. **Configure environment (optional):**

   Copy `.env.example` to `.env` and customize if needed:

   ```bash
   cp .env.example .env
   ```

   By default, browser-harness connects to `localhost:9222`. For Browser Use Cloud or custom endpoints, set `BU_CDP_URL`.

## Run

### Basic example

Execute a simple browser automation task:

```bash
python example.py
```

This script:
- Connects to your running Chrome instance
- Navigates to example.com
- Prints page info
- Takes a screenshot

### With Claude Code

Paste this prompt into Claude Code:

```text
Install or upgrade browser-harness to the latest stable version with uv using Python 3.12, register the skill from `browser-harness skill`, and connect it to my browser. Follow https://github.com/browser-use/browser-harness/blob/main/install.md if setup or connection fails.
```

Then ask Claude to perform browser tasks like:
- "Navigate to github.com and find trending repositories"
- "Search for Python tutorials on YouTube"
- "Fill out the contact form on example.com"

The agent will write custom helpers in `agent_helpers.py` as needed.

### Enable domain skills

For site-specific optimizations (GitHub, LinkedIn, Amazon, etc.):

```bash
export BH_DOMAIN_SKILLS=1
python example.py
```

Domain skills teach the agent selectors and workflows for common sites.

## Project Structure

```
.
├── example.py          # Basic browser automation script
├── requirements.txt    # Python dependencies
├── .env.example       # Environment variable template
└── README.md          # This file
```

## How it works

1. **browser-harness** connects to Chrome via CDP (Chrome DevTools Protocol)
2. Claude Code or your Python script calls browser-harness commands
3. The agent can write missing helpers to `agent_helpers.py` during execution
4. Domain skills provide reusable site-specific automation patterns

## Browser Use Cloud (optional)

For headless browsers with proxies and captcha solving:

1. Get a free API key: https://cloud.browser-use.com/new-api-key
2. Set `BU_CDP_URL` to your cloud browser endpoint
3. No local Chrome setup required

## Learn more

- [browser-harness GitHub](https://github.com/browser-use/browser-harness)
- [SKILL.md](https://github.com/browser-use/browser-harness/blob/main/SKILL.md) — day-to-day usage
- [Domain skills examples](https://github.com/browser-use/browser-harness/tree/main/agent-workspace/domain-skills)
