# Browser Harness + FastAPI Example

A minimal FastAPI application that exposes browser-harness automation capabilities via REST endpoints.

## Prerequisites

- Python 3.12+
- Chrome or Chromium with remote debugging enabled
- browser-harness installed and configured

## Setup

1. **Install dependencies:**

```bash
pip install -r requirements.txt
```

2. **Configure Chrome for remote debugging:**

Follow the setup from [browser-harness installation guide](https://github.com/browser-use/browser-harness/blob/main/install.md):

- Open `chrome://inspect/#remote-debugging`
- Enable "Discover network targets" and add `localhost:9222`
- Restart Chrome with `--remote-debugging-port=9222`

Or use a Browser Use Cloud browser by setting `BU_API_KEY`.

3. **Configure environment (optional):**

```bash
cp .env.example .env
# Edit .env to set BU_CDP_URL or BU_API_KEY if needed
```

## Run

Start the FastAPI server:

```bash
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`.

View interactive docs at `http://localhost:8000/docs`.

## Usage Examples

### Navigate to a URL

```bash
curl -X POST "http://localhost:8000/navigate?url=https://example.com"
```

### Execute custom browser-harness script

```bash
curl -X POST "http://localhost:8000/execute" \
  -H "Content-Type: application/json" \
  -d '{
    "script": "from browser_harness import page_info\nprint(page_info())"
  }'
```

### With custom CDP URL

```bash
curl -X POST "http://localhost:8000/execute" \
  -H "Content-Type: application/json" \
  -d '{
    "script": "from browser_harness import navigate\nnavigate('https://github.com')",
    "cdp_url": "ws://localhost:9222/devtools/browser/xyz"
  }'
```

## API Endpoints

- `GET /` - Health check
- `POST /execute` - Execute a browser-harness Python script
- `POST /navigate` - Navigate to a URL and return page info

## How It Works

This example wraps the `browser-harness` CLI, which connects to Chrome via CDP. Each request:

1. Accepts a Python script using browser-harness helpers
2. Passes it to the `browser-harness` command via stdin
3. Returns the output or error

The FastAPI server acts as a REST gateway to browser automation, useful for:

- Integrating browser automation into larger systems
- Triggering browser tasks from webhooks or schedulers
- Building browser automation microservices

## Notes

- Scripts execute with a 60-second timeout by default
- The browser must be running with remote debugging enabled
- Use Browser Use Cloud for serverless/headless deployment
- See [browser-harness docs](https://github.com/browser-use/browser-harness) for available helpers