**Browser Harness** is a lightweight Python CDP harness that connects LLMs directly to your browser—one WebSocket to Chrome, nothing between. This cookbook shows how to use Browser Harness to automate Next.js development workflows: testing your Next.js app's UI, scraping server-rendered pages, verifying route behavior, and letting an agent write missing helpers during execution.

Next.js apps often require browser-based validation (client hydration, dynamic routes, streaming SSR). Browser Harness gives you a thin layer over Chrome DevTools Protocol so you can script interactions, extract data, and build self-improving automation that adapts as your Next.js app evolves.

## How to Install Browser Harness and Connect to Chrome

Before automating your Next.js app, you need to install browser-harness and configure Chrome for remote debugging so the harness can connect via CDP.

**Prerequisites**
- Python 3.12+
- Chrome or Chromium installed
- pip or uv package manager

```bash
# Install browser-harness
pip install browser-harness

# Start Chrome with remote debugging enabled (macOS example)
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 \
  --user-data-dir=/tmp/chrome-debug-profile &

# Verify the harness can connect
browser-harness <<'PY'
print(page_info())
PY
```

The `pip install browser-harness` command installs the package and the `browser-harness` CLI. Chrome must be launched with `--remote-debugging-port=9222` to expose the CDP endpoint.

The `--user-data-dir` flag points to a temporary profile so your main browser session isn't affected. Once Chrome is running, the `browser-harness` CLI can execute Python snippets that call harness helpers like `page_info()`—this returns the current tab's URL, title, and metadata.

Browser Harness looks for Chrome at `http://localhost:9222` by default. If you use a different port or remote browser, set the `BU_CDP_URL` environment variable (e.g., `BU_CDP_URL=http://localhost:9223`).

**Expected output**

```
{'url': 'chrome://newtab/', 'title': 'New Tab', 'targetId': '...', 'type': 'page'}
```

**Gotchas**
- On macOS, you may need to allow remote debugging in System Settings → Privacy & Security after the first connection attempt.
- Chrome 144+ shows a per-attach popup—click 'Allow' when it appears.
- If Chrome is already running, close it completely before launching with `--remote-debugging-port`.

## How to Navigate to a Next.js Dev Server and Wait for Hydration

You want to open your Next.js app's dev server (e.g., http://localhost:3000), wait for the page to fully load and hydrate, then verify it's ready before running tests or scraping.

**Prerequisites**
- browser-harness installed
- Chrome running with remote debugging
- Next.js dev server running on localhost:3000

```python
# navigate_nextjs_app.py
import time

def navigate_and_wait(url: str, timeout: int = 10) -> dict:
    """Navigate to Next.js app and wait for client hydration."""
    # Use browser-harness helpers (assume these are available in the agent-workspace context)
    # page_info(), navigate(), wait_for_selector() are harness built-ins or agent-written helpers
    
    # Navigate to the URL
    navigate(url)
    
    # Wait for Next.js hydration marker (next-data script or body class)
    start = time.time()
    while time.time() - start < timeout:
        info = page_info()
        if 'localhost:3000' in info['url']:
            # Check for Next.js hydration signal (e.g., __NEXT_DATA__ script)
            has_next_data = evaluate_js(
                "document.getElementById('__NEXT_DATA__') !== null"
            )
            if has_next_data:
                print(f"Next.js app hydrated: {info['title']}")
                return info
        time.sleep(0.5)
    
    raise TimeoutError(f"Next.js app did not hydrate within {timeout}s")

# Run it
if __name__ == '__main__':
    result = navigate_and_wait('http://localhost:3000')
    print(result)
```

This recipe uses the `navigate()` helper (part of the harness or agent-written in `agent_helpers.py`) to open the Next.js dev server URL. Next.js injects a `<script id="__NEXT_DATA__">` tag containing page props after hydration, so we poll using `evaluate_js()` to check for its presence.

`page_info()` returns the current tab's URL and title. We loop with a timeout to give Next.js time to hydrate on slower machines or large pages. Once `__NEXT_DATA__` exists, we know React has taken over and the page is interactive.

The harness design assumes helpers like `navigate()` and `evaluate_js()` are either built-in or were written by the agent in a previous run and saved to `agent_helpers.py`. If they don't exist yet, the agent will generate them when it encounters the need.

**Expected output**

```
Next.js app hydrated: Home | My Next.js App
{'url': 'http://localhost:3000/', 'title': 'Home | My Next.js App', 'targetId': '...', 'type': 'page'}
```

**Gotchas**
- Next.js Fast Refresh can cause the page to reload during dev—add a small delay after navigation if tests flake.
- Server-side rendered pages may appear loaded before hydration completes; always check for client-side markers like __NEXT_DATA__ or React root attributes.
- If your Next.js app uses a custom _document.js that omits __NEXT_DATA__, check for a different hydration signal (e.g., body class or data-reactroot).

## How to Test a Next.js Dynamic Route

You want to verify that a Next.js dynamic route (e.g., /posts/[id]) renders correctly with different parameters and returns the expected content.

**Prerequisites**
- browser-harness installed
- Next.js app with dynamic routes running
- Agent-written helpers in agent_helpers.py (navigate, evaluate_js, page_info)

```python
# test_dynamic_route.py
import json

def test_nextjs_dynamic_route(route_template: str, test_cases: list[dict]) -> list[dict]:
    """Test Next.js dynamic routes with multiple parameter sets."""
    results = []
    
    for case in test_cases:
        route = route_template.format(**case['params'])
        url = f"http://localhost:3000{route}"
        
        # Navigate to the dynamic route
        navigate(url)
        time.sleep(1)  # Wait for Next.js to render
        
        info = page_info()
        
        # Extract page props from __NEXT_DATA__
        next_data = evaluate_js("""
            const script = document.getElementById('__NEXT_DATA__');
            script ? JSON.parse(script.textContent) : null;
        """)
        
        # Validate expected content
        page_props = next_data.get('props', {}).get('pageProps', {}) if next_data else {}
        
        results.append({
            'url': url,
            'title': info['title'],
            'params': case['params'],
            'props': page_props,
            'passed': case['expected_key'] in page_props
        })
        
        print(f"✓ {route}: {info['title']}")
    
    return results

# Test /posts/[id] route
test_cases = [
    {'params': {'id': '1'}, 'expected_key': 'post'},
    {'params': {'id': '42'}, 'expected_key': 'post'},
    {'params': {'id': 'nonexistent'}, 'expected_key': 'error'}
]

results = test_nextjs_dynamic_route('/posts/{id}', test_cases)
print(json.dumps(results, indent=2))
```

This recipe tests Next.js dynamic routes by navigating to multiple instances of the same route pattern with different parameters. It uses `navigate()` to load each URL, then extracts the `__NEXT_DATA__` script content to inspect the server-passed `pageProps`.

Next.js serializes page props into this script tag during SSR, so it's the most reliable way to verify what data the route received. We parse the JSON and check for expected keys (e.g., `post` for valid IDs, `error` for invalid ones).

The function returns a list of test results with pass/fail status. This pattern works for catch-all routes (`[...slug]`) and optional catch-all routes (`[[...slug]]`) by adjusting the `route_template` string.

If the agent hasn't written `navigate()` or `evaluate_js()` yet, it will generate them in `agent_helpers.py` when you first run this script.

**Expected output**

```
✓ /posts/1: Post 1 | My Next.js App
✓ /posts/42: Post 42 | My Next.js App
✓ /posts/nonexistent: 404 - Not Found
[
  {"url": "http://localhost:3000/posts/1", "title": "Post 1 | My Next.js App", "params": {"id": "1"}, "props": {"post": {...}}, "passed": true},
  ...
]
```

**Gotchas**
- Next.js 13+ App Router uses a different data structure (RSC payload) instead of __NEXT_DATA__. For App Router, inspect the streamed HTML or use React DevTools protocol.
- getServerSideProps and getStaticProps both use __NEXT_DATA__, but ISR/stale data may cache. Clear the .next cache if tests return unexpected props.
- Dynamic imports and Suspense boundaries can delay content rendering. Add explicit waits for critical elements if props are present but UI isn't fully painted.

## How to Scrape Server-Side Rendered Next.js Pages

You want to extract structured data from a Next.js SSR page (product listings, blog posts, pricing tables) by parsing the server-rendered HTML or the __NEXT_DATA__ payload.

**Prerequisites**
- browser-harness installed
- Target Next.js site accessible
- Basic understanding of Next.js data fetching (getServerSideProps, getStaticProps)

```python
# scrape_nextjs_ssr.py
import json

def scrape_nextjs_page(url: str) -> dict:
    """Scrape data from a Next.js SSR page."""
    navigate(url)
    time.sleep(2)  # Wait for page load
    
    info = page_info()
    
    # Extract __NEXT_DATA__ (contains server props)
    next_data_raw = evaluate_js("""
        const script = document.getElementById('__NEXT_DATA__');
        script ? script.textContent : null;
    """)
    
    if not next_data_raw:
        # Fallback: scrape visible HTML if __NEXT_DATA__ is missing
        html_content = evaluate_js("document.documentElement.outerHTML")
        return {
            'url': url,
            'title': info['title'],
            'html': html_content,
            'method': 'html_fallback'
        }
    
    next_data = json.loads(next_data_raw)
    page_props = next_data.get('props', {}).get('pageProps', {})
    
    return {
        'url': url,
        'title': info['title'],
        'page_props': page_props,
        'build_id': next_data.get('buildId'),
        'method': 'next_data'
    }

# Example: scrape a Next.js blog listing
result = scrape_nextjs_page('https://example-nextjs-blog.com/posts')
print(json.dumps(result, indent=2))

# Extract specific fields (e.g., post titles)
if 'page_props' in result and 'posts' in result['page_props']:
    posts = result['page_props']['posts']
    print(f"Found {len(posts)} posts:")
    for post in posts[:5]:
        print(f"  - {post.get('title', 'Untitled')}")
```

Scraping Next.js SSR pages is cleaner than traditional HTML parsing because Next.js serializes all server-fetched data into the `__NEXT_DATA__` script. This recipe extracts that script's content using `evaluate_js()`, parses it as JSON, and pulls out `pageProps`—the exact data passed to the React component.

If `__NEXT_DATA__` isn't present (e.g., a static export or custom HTML), the script falls back to scraping the raw HTML. The harness runs in a real browser, so all JavaScript execution and DOM manipulation is complete before extraction.

This approach works for:
- Blog post listings
- E-commerce product pages
- Pricing tables
- Any SSR Next.js page with structured data

The `buildId` field helps verify the deployment version. Compare it across scrapes to detect when the site updates.

**Expected output**

```
{
  "url": "https://example-nextjs-blog.com/posts",
  "title": "Blog Posts | Example",
  "page_props": {
    "posts": [{"id": 1, "title": "First Post", "excerpt": "..."}],
    "pagination": {"page": 1, "total": 42}
  },
  "build_id": "abc123",
  "method": "next_data"
}
Found 10 posts:
  - First Post
  - Second Post
  ...
```

**Gotchas**
- Next.js 13+ App Router pages use RSC (React Server Components) and may not include __NEXT_DATA__. For App Router, parse the streamed HTML or use Chrome DevTools Protocol's DOM snapshot.
- Pages with client-side data fetching (SWR, React Query) won't have all data in __NEXT_DATA__. Wait for network requests to complete or check for loading states.
- Rate limiting: if scraping multiple pages, add delays between navigations. Some Next.js sites detect rapid CDP connections as bots.

## How to Verify Next.js Middleware Redirects and Rewrites

You want to test that Next.js middleware correctly redirects users (e.g., /old-path → /new-path) or rewrites URLs without changing the browser location, and capture the final URL and response status.

**Prerequisites**
- browser-harness installed
- Next.js app with middleware configured
- Chrome with remote debugging enabled

```python
# test_nextjs_middleware.py
import time

def test_middleware_redirect(start_url: str, expected_final_url: str) -> dict:
    """Test Next.js middleware redirect behavior."""
    navigate(start_url)
    time.sleep(1)  # Wait for redirect to complete
    
    info = page_info()
    final_url = info['url']
    
    # Check if redirect happened
    redirect_occurred = final_url != start_url
    redirect_correct = final_url == expected_final_url
    
    # Get response status from performance timing (if available)
    perf_data = evaluate_js("""
        const nav = performance.getEntriesByType('navigation')[0];
        nav ? {
            responseStatus: nav.responseStatus || 'unknown',
            transferSize: nav.transferSize,
            type: nav.type
        } : null;
    """)
    
    return {
        'start_url': start_url,
        'final_url': final_url,
        'expected_url': expected_final_url,
        'redirect_occurred': redirect_occurred,
        'redirect_correct': redirect_correct,
        'performance': perf_data,
        'passed': redirect_correct
    }

def test_middleware_rewrite(url: str, expected_title: str) -> dict:
    """Test Next.js middleware rewrite (URL stays same, content changes)."""
    navigate(url)
    time.sleep(1)
    
    info = page_info()
    
    # For rewrites, URL should not change
    url_unchanged = info['url'] == url
    
    # But the rendered content should match the rewrite target
    title_correct = expected_title in info['title']
    
    # Extract props to verify rewrite target was rendered
    next_data = evaluate_js("""
        const script = document.getElementById('__NEXT_DATA__');
        script ? JSON.parse(script.textContent) : null;
    """)
    
    page_path = next_data.get('page') if next_data else None
    
    return {
        'url': url,
        'final_url': info['url'],
        'url_unchanged': url_unchanged,
        'title': info['title'],
        'title_correct': title_correct,
        'rendered_page': page_path,
        'passed': url_unchanged and title_correct
    }

# Test a redirect
redirect_result = test_middleware_redirect(
    'http://localhost:3000/old-blog',
    'http://localhost:3000/blog'
)
print(f"Redirect test: {'✓ PASS' if redirect_result['passed'] else '✗ FAIL'}")
print(redirect_result)

# Test a rewrite
rewrite_result = test_middleware_rewrite(
    'http://localhost:3000/products/special',
    'Special Products'
)
print(f"Rewrite test: {'✓ PASS' if rewrite_result['passed'] else '✗ FAIL'}")
print(rewrite_result)
```

Next.js middleware runs on the Edge runtime and can redirect or rewrite requests before they reach page components. This recipe tests both behaviors by comparing URLs and rendered content.

For **redirects**, we navigate to the start URL and check if the browser's final URL matches the expected destination. The `page_info()` helper returns the current location after all redirects complete. We also extract performance timing data to verify the response type (`navigate` vs. `reload`).

For **rewrites**, the URL should remain unchanged (that's the point of a rewrite—transparent to the user), but the page content should come from the rewrite target. We verify this by checking that:
1. The final URL equals the start URL
2. The page title matches the expected rewrite target
3. The `__NEXT_DATA__` page field shows the rewritten page path

The harness executes in a real Chrome instance, so all middleware logic (geolocation-based redirects, A/B tests, auth checks) runs exactly as it would for real users.

**Expected output**

```
Redirect test: ✓ PASS
{'start_url': 'http://localhost:3000/old-blog', 'final_url': 'http://localhost:3000/blog', 'expected_url': 'http://localhost:3000/blog', 'redirect_occurred': True, 'redirect_correct': True, 'performance': {'responseStatus': 200, 'transferSize': 1234, 'type': 'navigate'}, 'passed': True}

Rewrite test: ✓ PASS
{'url': 'http://localhost:3000/products/special', 'final_url': 'http://localhost:3000/products/special', 'url_unchanged': True, 'title': 'Special Products | My Store', 'title_correct': True, 'rendered_page': '/products/[category]', 'passed': True}
```

**Gotchas**
- Next.js middleware redirects use 307 (Temporary Redirect) by default, not 301. Check your middleware config if you need permanent redirects.
- Rewrites are invisible to the browser—there's no responseStatus or redirect entry in performance timing. Verify by inspecting __NEXT_DATA__ or the rendered component tree.
- Middleware runs on every request, including static assets. If testing a route that loads many resources, add a delay to ensure all requests complete before inspecting the page.
- Edge runtime middleware can't access Node.js APIs. If your middleware fails in production but works locally, check for Node-specific code (fs, crypto) that doesn't run on the Edge.

## How to Let the Agent Write a Missing Next.js Helper During Execution

You want to automate a Next.js-specific task (e.g., uploading a file to a Next.js API route, or interacting with a custom form), but the helper function doesn't exist yet. Browser Harness should let the agent write the helper on the fly.

**Prerequisites**
- browser-harness installed
- Agent workspace configured (agent_helpers.py exists)
- LLM agent capable of writing Python code

```python
# demonstrate_self_improving_helper.py
# This script shows how the agent workflow detects a missing helper and writes it.

# Step 1: Try to call a helper that doesn't exist
try:
    result = upload_file_to_nextjs_api(
        api_url='http://localhost:3000/api/upload',
        file_path='/tmp/test-image.png'
    )
    print(f"Upload succeeded: {result}")
except NameError as e:
    print(f"Helper missing: {e}")
    print("Agent will now write upload_file_to_nextjs_api() to agent_helpers.py...")
    
    # Step 2: Agent writes the helper (this happens automatically in practice)
    # For demonstration, we show what the agent would generate:
    new_helper_code = '''
import os
import base64

def upload_file_to_nextjs_api(api_url: str, file_path: str) -> dict:
    """Upload a file to a Next.js API route using CDP fetch."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    # Read file and base64 encode
    with open(file_path, 'rb') as f:
        file_data = base64.b64encode(f.read()).decode('utf-8')
    
    filename = os.path.basename(file_path)
    
    # Create form data payload
    form_boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'
    form_body = (
        f'--{form_boundary}\r\n'
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f'Content-Type: application/octet-stream\r\n\r\n'
        f'{file_data}\r\n'
        f'--{form_boundary}--\r\n'
    )
    
    # Use evaluate_js to fetch via browser
    response_text = evaluate_js(f"""
        (async () => {{
            const res = await fetch('{api_url}', {{
                method: 'POST',
                headers: {{
                    'Content-Type': 'multipart/form-data; boundary={form_boundary}'
                }},
                body: `{form_body}`
            }});
            return await res.text();
        }})()
    """)
    
    return {'status': 'uploaded', 'response': response_text}
'''
    
    # Agent appends this to agent_helpers.py
    helpers_path = os.path.expanduser('~/.config/browser-harness/agent-workspace/agent_helpers.py')
    with open(helpers_path, 'a') as f:
        f.write('\n\n' + new_helper_code)
    
    print(f"✓ Helper written to {helpers_path}")
    
    # Step 3: Reload and retry
    exec(open(helpers_path).read(), globals())
    result = upload_file_to_nextjs_api(
        api_url='http://localhost:3000/api/upload',
        file_path='/tmp/test-image.png'
    )
    print(f"Upload succeeded: {result}")
```

This recipe demonstrates Browser Harness's core philosophy: **the agent writes missing helpers during execution**. When you try to call `upload_file_to_nextjs_api()` and it doesn't exist, the agent:

1. Detects the `NameError`
2. Generates the helper function (using context about Next.js API routes and CDP)
3. Appends it to `agent_helpers.py` in the agent workspace (`~/.config/browser-harness/agent-workspace/`)
4. Reloads the helpers file and retries the call

The generated helper uses `evaluate_js()` to run `fetch()` inside the browser context, so cookies, CORS, and same-origin policies behave exactly as they would for a real user. This is more reliable than Python's `requests` library for Next.js apps that use middleware or authentication.

Over time, `agent_helpers.py` accumulates all the custom functions the agent has written for your workflows (uploading files, filling forms, scraping specific selectors). Each run improves the harness. You can also manually edit `agent_helpers.py` or move frequently-used helpers into `domain-skills/` for reuse across projects.

In a real agent session (Claude Code, Cursor, Codex CLI), the agent handles all of this automatically—you just describe the task, and it writes the missing code.

**Expected output**

```
Helper missing: name 'upload_file_to_nextjs_api' is not defined
Agent will now write upload_file_to_nextjs_api() to agent_helpers.py...
✓ Helper written to /Users/you/.config/browser-harness/agent-workspace/agent_helpers.py
Upload succeeded: {'status': 'uploaded', 'response': '{"fileUrl":"/uploads/test-image.png"}'}
```

**Gotchas**
- The agent writes helpers to agent_helpers.py in your config directory (XDG_CONFIG_HOME or ~/.config), not your project directory. Sync this file across machines if needed.
- Helper functions use evaluate_js() to run code in the browser, so they inherit the page's origin and security context. API routes that require authentication must have a logged-in session in the browser.
- Self-improving harnesses can accumulate stale or redundant helpers over time. Periodically review agent_helpers.py and refactor duplicates into domain-skills.
- If the agent generates an incorrect helper, manually edit agent_helpers.py to fix it—the next run will use your corrected version.

## How to Run Browser Harness Against a Remote Next.js App in Browser Use Cloud

You want to run Browser Harness automation against a remote, production Next.js site without exposing your local browser, or you need stealth/captcha solving for scraping protected Next.js apps.

**Prerequisites**
- browser-harness installed
- Browser Use Cloud account (free tier available)
- BU_CDP_URL or cloud browser API key

```bash
# Get a Browser Use Cloud API key (free tier: 3 concurrent browsers)
# Visit https://cloud.browser-use.com/new-api-key or let the agent sign up via docs.browser-use.com/llms.txt

# Set the cloud browser URL as the CDP endpoint
export BU_CDP_URL="wss://cloud.browser-use.com/YOUR_API_KEY/connect"

# Run your Next.js automation script
browser-harness <<'PY'
import json

# Navigate to a production Next.js site
navigate('https://production-nextjs-app.com')
time.sleep(2)

# Extract data (same helpers work locally or in the cloud)
next_data = evaluate_js("""
    const script = document.getElementById('__NEXT_DATA__');
    script ? JSON.parse(script.textContent) : null;
""")

if next_data:
    print(json.dumps(next_data.get('props', {}), indent=2))
else:
    print("No __NEXT_DATA__ found")

print(f"Final URL: {page_info()['url']}")
PY
```

Browser Use Cloud provides managed Chrome instances with stealth, proxies, and captcha solving—useful for production Next.js apps that block automated browsers. By setting `BU_CDP_URL` to a cloud browser WebSocket URL, all Browser Harness commands route through the cloud instance instead of your local Chrome.

The free tier includes 3 concurrent browsers, no credit card required. Get a key at [cloud.browser-use.com/new-api-key](https://cloud.browser-use.com/new-api-key), or let the agent sign up itself by reading [docs.browser-use.com/llms.txt](https://docs.browser-use.com/llms.txt) (includes setup flow and challenge context).

All helpers (`navigate()`, `evaluate_js()`, `page_info()`) work identically whether the browser is local or remote—the harness abstracts the CDP connection. This makes it easy to develop locally, then deploy to cloud browsers for production scraping or testing.

**Use cases for Browser Use Cloud + Next.js:**
- Scraping competitor Next.js sites that block automated tools
- Running CI/CD tests against deployed Next.js apps without managing headless Chrome
- Bypassing rate limits or geo-restrictions with rotating proxies
- Solving captchas on Next.js auth flows

**Expected output**

```
{
  "pageProps": {
    "products": [...],
    "categories": [...]
  },
  "__N_SSG": true
}
Final URL: https://production-nextjs-app.com/
```

**Gotchas**
- Cloud browsers have a session timeout (typically 15 minutes of inactivity). Keep the connection alive with periodic page_info() calls if your automation runs longer.
- Browser Use Cloud browsers use residential proxies by default. Some Next.js apps detect proxies and serve different content (e.g., showing a captcha). Check the 'stealth' setting in your cloud config.
- The BU_CDP_URL format is wss://cloud.browser-use.com/<API_KEY>/connect. Omit /connect and the connection will fail.
- Free tier browsers share IPs with other users. Upgrade to a paid plan if you need dedicated IPs or higher concurrency.

## FAQ

### Can Browser Harness test Next.js App Router (React Server Components)?

Yes, but App Router pages use a different serialization format (RSC payload) instead of __NEXT_DATA__. You can still scrape the rendered HTML or use Chrome DevTools Protocol's DOM snapshot. The agent can write a helper to parse RSC streams if needed.

### How do I handle Next.js authentication (e.g., NextAuth.js) in Browser Harness?

Browser Harness runs in a real Chrome instance, so you can manually log in once, then all subsequent automation uses the authenticated session. Alternatively, write a helper to fill the login form programmatically using evaluate_js() to submit credentials and wait for the session cookie.

### What's the difference between browser-harness and traditional Next.js E2E testing (Playwright, Cypress)?

Browser Harness is agent-first: the LLM writes missing helpers during execution, so you describe tasks in natural language instead of writing test scripts. Playwright/Cypress are human-authored test frameworks with predefined APIs. Use Browser Harness for exploratory automation and self-improving workflows; use Playwright/Cypress for stable, version-controlled test suites.

### Can I deploy Browser Harness automation to CI/CD for Next.js apps?

Yes. Set BU_CDP_URL to a Browser Use Cloud browser endpoint, or run Chrome with --remote-debugging-port in your CI container. The agent-workspace (agent_helpers.py and domain-skills/) should be committed to your repo so helpers persist across runs.

### Why use Browser Harness instead of scraping Next.js API routes directly?

Next.js apps often render data client-side (SWR, React Query) or use middleware that modifies responses based on headers/cookies. Browser Harness sees the full rendered page, including client-side hydration and dynamic imports, so you get the exact user experience. API scraping misses this.

## Key takeaways

- Browser Harness connects LLMs directly to Chrome via CDP—one WebSocket, no middleware—so agents can automate Next.js apps with real browser context (cookies, CORS, hydration).
- Next.js serializes server-fetched data into the __NEXT_DATA__ script tag, making SSR pages trivial to scrape. Extract page props as JSON instead of parsing HTML.
- The agent writes missing helpers (file uploads, form fills, custom selectors) to agent_helpers.py during execution, so the harness improves itself every run.
- Test Next.js dynamic routes, middleware redirects, and rewrites by navigating to URLs and inspecting page_info() and performance timing—all in a real browser.
- Use Browser Use Cloud browsers (free tier: 3 concurrent) for stealth, captcha solving, or CI/CD deployments. Set BU_CDP_URL and all helpers work identically.
- Browser Harness is agent-first automation: describe the task, the agent generates the code. Traditional E2E frameworks (Playwright, Cypress) require you to write scripts yourself.