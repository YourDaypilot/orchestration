"""
Trace Logger - Comprehensive file-based logging system
All system operations are logged to trace/ folder for debugging
NO console logs - everything stored in files
"""
import os
import json
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
from functools import wraps
import threading

class TraceLogger:
    """
    File-based trace logging system for comprehensive debugging
    All logs stored in trace/ folder with timestamps and context
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.trace_dir = Path(__file__).parent.parent / "trace"
            self.trace_dir.mkdir(exist_ok=True)

            # Create dated log file
            today = datetime.now().strftime("%Y-%m-%d")
            self.current_log_file = self.trace_dir / f"trace_{today}.log"
            self.error_log_file = self.trace_dir / f"error_{today}.log"
            self.debug_log_file = self.trace_dir / f"debug_{today}.log"

            # Create session file for current run
            session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.session_log_file = self.trace_dir / f"session_{session_id}.log"

            self.initialized = True
            self._write_startup_marker()

    def _write_startup_marker(self):
        """Write startup marker to all log files"""
        marker = f"\n{'='*80}\n" \
                f"SESSION START: {datetime.now().isoformat()}\n" \
                f"{'='*80}\n"

        for log_file in [self.current_log_file, self.session_log_file]:
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(marker)

    def _format_log_entry(self, level: str, message: str, context: Optional[Dict] = None,
                         module: str = "", function: str = "", line: int = 0) -> str:
        """Format log entry with full context"""
        timestamp = datetime.now().isoformat()

        log_entry = {
            "timestamp": timestamp,
            "level": level,
            "module": module,
            "function": function,
            "line": line,
            "message": message,
            "context": context or {}
        }

        # Human-readable format
        formatted = f"[{timestamp}] [{level}] {module}::{function}:{line}\n"
        formatted += f"  Message: {message}\n"
        if context:
            formatted += f"  Context: {json.dumps(context, indent=2, ensure_ascii=False)}\n"
        formatted += "-" * 80 + "\n"

        return formatted

    def _write_to_file(self, filepath: Path, content: str):
        """Thread-safe file writing"""
        with self._lock:
            try:
                with open(filepath, 'a', encoding='utf-8') as f:
                    f.write(content)
            except Exception as e:
                # Last resort - write to emergency log
                emergency_log = self.trace_dir / "emergency.log"
                with open(emergency_log, 'a', encoding='utf-8') as f:
                    f.write(f"[{datetime.now().isoformat()}] LOGGING ERROR: {str(e)}\n")
                    f.write(f"Failed to write: {content}\n")

    def debug(self, message: str, context: Optional[Dict] = None,
             module: str = "", function: str = "", line: int = 0):
        """Log debug level message"""
        entry = self._format_log_entry("DEBUG", message, context, module, function, line)
        self._write_to_file(self.debug_log_file, entry)
        self._write_to_file(self.session_log_file, entry)

    def info(self, message: str, context: Optional[Dict] = None,
            module: str = "", function: str = "", line: int = 0):
        """Log info level message"""
        entry = self._format_log_entry("INFO", message, context, module, function, line)
        self._write_to_file(self.current_log_file, entry)
        self._write_to_file(self.session_log_file, entry)

    def warning(self, message: str, context: Optional[Dict] = None,
               module: str = "", function: str = "", line: int = 0):
        """Log warning level message"""
        entry = self._format_log_entry("WARNING", message, context, module, function, line)
        self._write_to_file(self.current_log_file, entry)
        self._write_to_file(self.session_log_file, entry)

    def error(self, message: str, context: Optional[Dict] = None,
             module: str = "", function: str = "", line: int = 0,
             exception: Optional[Exception] = None):
        """Log error level message with optional exception"""
        if exception:
            context = context or {}
            context["exception_type"] = type(exception).__name__
            context["exception_message"] = str(exception)
            context["traceback"] = traceback.format_exc()

        entry = self._format_log_entry("ERROR", message, context, module, function, line)
        self._write_to_file(self.error_log_file, entry)
        self._write_to_file(self.current_log_file, entry)
        self._write_to_file(self.session_log_file, entry)

    def critical(self, message: str, context: Optional[Dict] = None,
                module: str = "", function: str = "", line: int = 0,
                exception: Optional[Exception] = None):
        """Log critical level message"""
        if exception:
            context = context or {}
            context["exception_type"] = type(exception).__name__
            context["exception_message"] = str(exception)
            context["traceback"] = traceback.format_exc()

        entry = self._format_log_entry("CRITICAL", message, context, module, function, line)
        # Critical errors go to all logs
        for log_file in [self.error_log_file, self.current_log_file, self.session_log_file]:
            self._write_to_file(log_file, entry)

    def trace_function_call(self, func_name: str, args: tuple, kwargs: dict,
                          module: str = "", line: int = 0):
        """Trace function call with parameters"""
        context = {
            "args": str(args),
            "kwargs": str(kwargs)
        }
        self.debug(f"Function call: {func_name}", context, module, func_name, line)

    def trace_function_return(self, func_name: str, result: Any,
                            module: str = "", line: int = 0):
        """Trace function return value"""
        context = {
            "return_value": str(result),
            "return_type": type(result).__name__
        }
        self.debug(f"Function return: {func_name}", context, module, func_name, line)

    def trace_state_change(self, component: str, old_state: Any, new_state: Any,
                          module: str = "", line: int = 0):
        """Trace state changes in components"""
        context = {
            "component": component,
            "old_state": str(old_state),
            "new_state": str(new_state)
        }
        self.info(f"State change in {component}", context, module, "state_change", line)

    def trace_api_call(self, endpoint: str, method: str, params: Dict,
                      module: str = "", line: int = 0):
        """Trace API calls"""
        context = {
            "endpoint": endpoint,
            "method": method,
            "parameters": params
        }
        self.info(f"API call: {method} {endpoint}", context, module, "api_call", line)

    def trace_api_response(self, endpoint: str, status_code: int, response: Any,
                          duration_ms: float, module: str = "", line: int = 0):
        """Trace API responses"""
        context = {
            "endpoint": endpoint,
            "status_code": status_code,
            "response": str(response)[:500],  # Limit response size
            "duration_ms": duration_ms
        }
        self.info(f"API response: {endpoint} [{status_code}]", context, module, "api_response", line)

    def trace_workflow_step(self, workflow_id: str, step_name: str, status: str,
                           data: Optional[Dict] = None, module: str = "", line: int = 0):
        """Trace workflow execution steps"""
        context = {
            "workflow_id": workflow_id,
            "step": step_name,
            "status": status,
            "data": data or {}
        }
        self.info(f"Workflow step: {workflow_id}/{step_name} -> {status}",
                 context, module, "workflow", line)


# Global trace logger instance
trace = TraceLogger()


def trace_calls(func):
    """Decorator to automatically trace function calls and returns"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        module = func.__module__
        func_name = func.__name__

        # Trace call
        trace.trace_function_call(func_name, args, kwargs, module)

        try:
            result = func(*args, **kwargs)
            # Trace return
            trace.trace_function_return(func_name, result, module)
            return result
        except Exception as e:
            # Trace exception
            trace.error(
                f"Exception in {func_name}",
                context={"args": str(args), "kwargs": str(kwargs)},
                module=module,
                function=func_name,
                exception=e
            )
            raise

    return wrapper


def trace_async_calls(func):
    """Decorator to automatically trace async function calls and returns"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        module = func.__module__
        func_name = func.__name__

        # Trace call
        trace.trace_function_call(func_name, args, kwargs, module)

        try:
            result = await func(*args, **kwargs)
            # Trace return
            trace.trace_function_return(func_name, result, module)
            return result
        except Exception as e:
            # Trace exception
            trace.error(
                f"Exception in {func_name}",
                context={"args": str(args), "kwargs": str(kwargs)},
                module=module,
                function=func_name,
                exception=e
            )
            raise

    return wrapper
