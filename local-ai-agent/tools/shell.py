#!/usr/bin/env python3
"""
Shell execution helper utilities for the AI agent.
Handles safe command execution and output capture.
"""

import subprocess
import shlex
import tempfile
import os
from pathlib import Path
from typing import Optional, Tuple, List


DANGEROUS_COMMANDS = {
    'rm', 'del', 'format', 'mkfs', 'dd', 'shutdown', 'reboot',
    'sudo rm', 'sudo del', 'sudo format', 'sudo mkfs'
}


def is_dangerous_command(command: str) -> bool:
    """Check if a command is potentially dangerous."""
    cmd_lower = command.lower().strip()
    for dangerous in DANGEROUS_COMMANDS:
        if cmd_lower.startswith(dangerous):
            return True
    return False


def run_command(
    command: str,
    cwd: Optional[Path] = None,
    shell: bool = False,
    capture_output: bool = True,
    timeout: Optional[int] = None
) -> Tuple[int, str, str]:
    """
    Execute a shell command safely.
    
    Returns:
        (returncode, stdout, stderr)
    """
    if is_dangerous_command(command):
        return (1, "", f"Error: Command '{command}' is considered dangerous and was blocked.")
    
    cwd = Path(cwd) if cwd else Path.cwd()
    
    try:
        if shell:
            result = subprocess.run(
                command,
                shell=True,
                cwd=cwd,
                capture_output=capture_output,
                text=True,
                timeout=timeout
            )
        else:
            # Split command into parts for safer execution
            parts = shlex.split(command)
            result = subprocess.run(
                parts,
                cwd=cwd,
                capture_output=capture_output,
                text=True,
                timeout=timeout
            )
        
        stdout = result.stdout if result.stdout else ""
        stderr = result.stderr if result.stderr else ""
        
        return (result.returncode, stdout, stderr)
    
    except subprocess.TimeoutExpired:
        return (1, "", f"Error: Command timed out after {timeout} seconds")
    except Exception as e:
        return (1, "", f"Error executing command: {str(e)}")


def check_ollama_available() -> bool:
    """Check if Ollama is installed and available."""
    returncode, _, _ = run_command("ollama --version", capture_output=True)
    return returncode == 0


def get_ollama_model() -> str:
    """Get the Ollama model to use, with environment variable override."""
    import os
    return os.environ.get('LOCAL_AI_MODEL', 'qwen2.5-coder:14b')


def run_ollama(prompt: str, model: Optional[str] = None) -> Tuple[int, str, str]:
    """
    Run Ollama with a prompt and return the response.
    
    Uses a temporary file to pass the prompt to ollama run.
    This handles long prompts better than command-line arguments.
    
    Returns:
        (returncode, stdout, stderr)
    """
    if model is None:
        model = get_ollama_model()
    
    # Create temporary file for prompt
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        f.write(prompt)
        temp_file = f.name
    
    try:
        # Use cat to pipe prompt file to ollama run
        command = f'cat {shlex.quote(temp_file)} | ollama run {shlex.quote(model)}'
        
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        stdout = result.stdout if result.stdout else ""
        stderr = result.stderr if result.stderr else ""
        
        return (result.returncode, stdout, stderr)
    
    except subprocess.TimeoutExpired:
        return (1, "", "Error: Ollama request timed out")
    except Exception as e:
        return (1, "", f"Error running Ollama: {str(e)}")
    finally:
        # Clean up temp file
        try:
            os.unlink(temp_file)
        except OSError:
            pass

