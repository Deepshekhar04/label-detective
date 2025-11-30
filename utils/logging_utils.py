"""
Logging utilities for Label Detective application.
Provides structured JSON logging with trace IDs and span tracking.
"""

import logging
import json
import uuid
import time
from datetime import datetime
from typing import Any, Dict, Optional


class JSONFormatter(logging.Formatter):
    """Custom formatter that outputs logs as JSON."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "time": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "message": record.getMessage(),
        }

        # Add custom fields if present
        if hasattr(record, "trace_id"):
            log_data["trace_id"] = record.trace_id
        if hasattr(record, "session_id"):
            log_data["session_id"] = record.session_id
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        if hasattr(record, "agent"):
            log_data["agent"] = record.agent
        if hasattr(record, "tool"):
            log_data["tool"] = record.tool
        if hasattr(record, "duration_ms"):
            log_data["duration_ms"] = record.duration_ms

        return json.dumps(log_data)


def setup_logger(name: str = "label_detective", level: str = "INFO") -> logging.Logger:
    """
    Configure and return a logger with JSON formatting.

    Args:
        name: Logger name
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))

    # Remove existing handlers to avoid duplicates
    logger.handlers = []

    # Console handler with JSON formatter
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(JSONFormatter())
    logger.addHandler(console_handler)

    return logger


def create_trace_id() -> str:
    """
    Generate a unique trace ID for request tracing.

    Returns:
        UUID string for trace identification
    """
    return str(uuid.uuid4())


def log_span(
    logger: logging.Logger,
    trace_id: str,
    agent_name: str,
    tool_name: str,
    input_data: Any,
    output_data: Any,
    duration_ms: float,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> None:
    """
    Log a span event for a tool call with timing and context information.

    Args:
        logger: Logger instance
        trace_id: Trace identifier
        agent_name: Name of the agent making the call
        tool_name: Name of the tool being called
        input_data: Input parameters (will be truncated if large)
        output_data: Output result (will be summarized if large)
        duration_ms: Execution duration in milliseconds
        session_id: Optional session identifier
        user_id: Optional user identifier
    """
    # Truncate large inputs/outputs for logging
    input_summary = str(input_data)[:200] if input_data else ""
    output_summary = str(output_data)[:200] if output_data else ""

    extra = {
        "trace_id": trace_id,
        "agent": agent_name,
        "tool": tool_name,
        "duration_ms": duration_ms,
    }

    if session_id:
        extra["session_id"] = session_id
    if user_id:
        extra["user_id"] = user_id

    logger.info(
        f"Tool call: {agent_name}.{tool_name} completed in {duration_ms:.2f}ms",
        extra=extra,
    )


def get_logger(name: str) -> logging.Logger:
    """
    Get or create a logger instance.

    Args:
        name: Module or component name

    Returns:
        Logger instance
    """
    return logging.getLogger(f"label_detective.{name}")


class SpanTimer:
    """Context manager for timing operations and creating span logs."""

    def __init__(
        self,
        logger: logging.Logger,
        trace_id: str,
        agent_name: str,
        tool_name: str,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ):
        self.logger = logger
        self.trace_id = trace_id
        self.agent_name = agent_name
        self.tool_name = tool_name
        self.session_id = session_id
        self.user_id = user_id
        self.start_time = None
        self.input_data = None
        self.output_data = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = (time.time() - self.start_time) * 1000

        if exc_type is None:
            log_span(
                self.logger,
                self.trace_id,
                self.agent_name,
                self.tool_name,
                self.input_data,
                self.output_data,
                duration_ms,
                self.session_id,
                self.user_id,
            )
        else:
            # Log error span
            extra = {
                "trace_id": self.trace_id,
                "agent": self.agent_name,
                "tool": self.tool_name,
                "duration_ms": duration_ms,
                "error": str(exc_val),
            }
            if self.session_id:
                extra["session_id"] = self.session_id
            if self.user_id:
                extra["user_id"] = self.user_id

            self.logger.error(
                f"Tool call failed: {self.agent_name}.{tool_name}", extra=extra
            )

    def set_input(self, data: Any):
        """Set input data for logging."""
        self.input_data = data

    def set_output(self, data: Any):
        """Set output data for logging."""
        self.output_data = data
