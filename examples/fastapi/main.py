import os
import subprocess
import tempfile
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

app = FastAPI(title="Browser Harness FastAPI Example")


class BrowserTask(BaseModel):
    script: str
    cdp_url: Optional[str] = None


class BrowserTaskResult(BaseModel):
    success: bool
    output: str
    error: Optional[str] = None


@app.get("/")
def root():
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "browser-harness-fastapi",
        "endpoints": [
            "/execute - POST - Execute browser-harness script"
        ]
    }


@app.post("/execute", response_model=BrowserTaskResult)
def execute_browser_task(task: BrowserTask):
    """
    Execute a browser-harness Python script.
    
    The script should use browser-harness helpers like page_info(), navigate(), etc.
    Pass an optional CDP URL to connect to a specific Chrome instance.
    """
    try:
        # Prepare environment with CDP URL if provided
        env = os.environ.copy()
        if task.cdp_url:
            env["BU_CDP_URL"] = task.cdp_url
        
        # Write script to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(task.script)
            script_path = f.name
        
        try:
            # Execute via browser-harness CLI
            result = subprocess.run(
                ["browser-harness"],
                input=task.script,
                capture_output=True,
                text=True,
                env=env,
                timeout=60
            )
            
            if result.returncode == 0:
                return BrowserTaskResult(
                    success=True,
                    output=result.stdout
                )
            else:
                return BrowserTaskResult(
                    success=False,
                    output=result.stdout,
                    error=result.stderr
                )
        finally:
            # Clean up temp file
            if os.path.exists(script_path):
                os.unlink(script_path)
    
    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=408,
            detail="Script execution timed out after 60 seconds"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Execution error: {str(e)}"
        )


@app.post("/navigate")
def navigate_to_url(url: str):
    """
    Simple example: navigate to a URL and return page info.
    """
    script = f"""
from browser_harness import navigate, page_info

navigate('{url}')
print(page_info())
"""
    
    try:
        result = subprocess.run(
            ["browser-harness"],
            input=script,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            return {
                "success": True,
                "url": url,
                "page_info": result.stdout
            }
        else:
            return {
                "success": False,
                "error": result.stderr
            }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Navigation failed: {str(e)}"
        )