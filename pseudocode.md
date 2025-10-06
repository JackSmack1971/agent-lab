# Pseudocode for Fixing 14 Failing Tests in Agent-Lab Project

## Overview
This document provides detailed pseudocode fixes for 14 failing tests across streaming cancellation, UI integration, security validations, session handling, and content truncation categories.

## 1. Streaming Cancellation Fixes

### Issue: run_agent_stream Cancellation Timing
**Problem**: Cancellation token is checked after processing chunks, causing partial responses when immediate cancellation is expected.

**Current Implementation Issues**:
- Check `cancel_token.is_set()` occurs inside the async for loop after `getattr(chunk, "delta", None)`
- This allows one more chunk to be processed before cancellation takes effect
- Tests expect immediate abortion with no text accumulation

**Fix: Pre-emptive Cancellation Check**

```python
async def run_agent_stream_fixed(
    agent: Agent,
    user_message: str,
    on_delta: Callable[[str], None],
    cancel_token: Event,
    correlation_id: str | None = None,
) -> StreamResult:
    """
    Fixed streaming implementation with immediate cancellation response.

    Key improvements:
    - Check cancellation before processing any chunk
    - Immediate return on cancellation without any text accumulation
    - Proper async context management for stream cleanup
    """
    logger_bound = logger.bind(correlation_id=correlation_id) if correlation_id else logger

    logger_bound.info("Starting agent streaming", extra={
        "message_length": len(user_message),
        "agent_model": getattr(agent, 'model', 'unknown'),
    })

    loop = asyncio.get_running_loop()
    start_ts = loop.time()
    text_parts: list[str] = []
    usage: dict[str, Any] | None = None
    aborted = False

    def _usage_to_dict(raw_usage: Any) -> dict[str, Any] | None:
        if raw_usage is None:
            return None
        if isinstance(raw_usage, dict):
            return dict(raw_usage)
        if hasattr(raw_usage, "model_dump"):
            return raw_usage.model_dump()
        if hasattr(raw_usage, "dict"):
            return raw_usage.dict()
        try:
            return asdict(raw_usage)
        except TypeError:
            return None

    async def _consume_stream_immediate_cancel(stream_iter: Any) -> None:
        """
        Consume stream with immediate cancellation check.

        Checks cancel_token BEFORE processing each chunk to ensure
        no partial text accumulation on cancellation.
        """
        nonlocal usage, aborted
        try:
            async for chunk in stream_iter:
                # CRITICAL FIX: Check cancellation BEFORE processing chunk
                if cancel_token.is_set():
                    aborted = True
                    logger_bound.info("Streaming cancelled before chunk processing")
                    break

                delta = getattr(chunk, "delta", None)
                if isinstance(delta, str) and delta:
                    on_delta(delta)
                    text_parts.append(delta)

                # Only update usage if we haven't been cancelled
                if not aborted and usage is None:
                    response = getattr(chunk, "response", None)
                    if response is not None:
                        usage = _usage_to_dict(getattr(response, "usage", None))
        except Exception as e:
            logger_bound.error("Error during stream consumption", extra={"error": str(e)})
            raise

    # Main streaming logic with improved error handling
    try:
        stream_iterable = agent.run(user_message, stream=True)
    except TypeError:
        stream_iterable = None
    except Exception as exc:
        raise RuntimeError(f"Agent streaming failed: {exc}") from exc

    if stream_iterable is not None:
        if asyncio.iscoroutine(stream_iterable):
            stream_iterable = await stream_iterable
        await _consume_stream_immediate_cancel(stream_iterable)
    else:
        try:
            stream_ctx = agent.run_stream(user_message)
        except Exception as exc:
            raise RuntimeError(f"Agent streaming failed: {exc}") from exc

        async with stream_ctx as stream_response:
            text_stream = stream_response.stream_text(delta=True)
            try:
                async for delta_text in text_stream:
                    # CRITICAL FIX: Check cancellation BEFORE processing delta
                    if cancel_token.is_set():
                        aborted = True
                        logger_bound.info("Streaming cancelled before delta processing")
                        break
                    if delta_text:
                        on_delta(delta_text)
                        text_parts.append(delta_text)
            finally:
                if hasattr(text_stream, "aclose"):
                    await text_stream.aclose()

            if not aborted and usage is None:
                usage = _usage_to_dict(stream_response.usage())

    latency_ms = int((loop.time() - start_ts) * 1000)

    logger_bound.info("Agent streaming completed", extra={
        "response_length": len(text_parts),
        "latency_ms": latency_ms,
        "aborted": aborted,
        "usage_available": usage is not None,
    })

    return StreamResult("".join(text_parts), usage, latency_ms, aborted)
```

### Issue: Mock Streaming Response Timing
**Problem**: Test mocks don't simulate real async timing, causing cancellation tests to pass incorrectly.

**Fix: Realistic Async Mock with Proper Timing**

```python
class RealisticDelayedStream:
    """
    Mock streaming response that properly simulates async timing
    for cancellation testing.
    """
    def __init__(self, chunks: list[str], delay_between_chunks: float = 0.01):
        self.chunks = chunks
        self.delay = delay_between_chunks
        self.index = 0
        self.cancelled = False

    def __aiter__(self):
        return self

    async def __anext__(self):
        # Allow cancellation check to be tested
        await asyncio.sleep(0.001)  # Minimal delay to allow cancellation

        if self.index >= len(self.chunks):
            raise StopAsyncIteration

        # Simulate processing delay
        if self.index > 0:
            await asyncio.sleep(self.delay)

        chunk = Mock()
        chunk.delta = self.chunks[self.index]
        self.index += 1
        return chunk
```

## 2. UI Integration Fixes

### Issue: Async Generator State Management
**Problem**: send_message_streaming yields intermediate states but doesn't properly handle cancellation cleanup.

**Fix: Robust Async Generator with State Tracking**

```python
async def send_message_streaming_fixed(
    message: str,
    history: list[list[str]] | None,
    config_state: AgentConfig,
    model_source_enum: str,
    agent_state: Any,
    cancel_event_state: Event | None,
    is_generating_state: bool,
    experiment_id: str,
    task_label: str,
    run_notes: str,
    id_mapping: dict
) -> AsyncGenerator[tuple, None]:
    """
    Fixed streaming message handler with proper state management.

    Key improvements:
    - Immediate cancellation check before processing
    - Proper cleanup on cancellation
    - State validation before yielding
    - Error recovery with meaningful messages
    """
    correlation_id = f"stream_{asyncio.get_event_loop().time()}"

    try:
        # Input validation and sanitization
        if not message or not message.strip():
            yield (
                None,  # chat_history
                None,  # agent_display
                "Enter a message to send to the agent.",  # status_message
                gr.update(interactive=True),  # send_button
                gr.update(visible=False),  # cancel_button
                None,  # model_display
                None,  # agent_state
                cancel_event_state,  # cancel_event
                False,  # is_generating
                None,  # experiment_id_display
                None,  # task_label_display
                None,  # run_notes_display
                None,  # metadata_display
            )
            return

        sanitized_message = message.strip()
        if len(sanitized_message) > 10000:  # Reasonable message limit
            yield (
                None,
                None,
                "Message too long. Please limit to 10,000 characters.",
                gr.update(interactive=True),
                gr.update(visible=False),
                None, None, None, False, None, None, None, None
            )
            return

        # Check for immediate cancellation
        if cancel_event_state and cancel_event_state.is_set():
            yield (
                history,
                None,
                "Generation cancelled before starting.",
                gr.update(interactive=True),
                gr.update(visible=False),
                None, None, None, False, None, None, None, None
            )
            return

        # Build agent with error handling
        try:
            include_web = "web_fetch" in getattr(config_state, 'tools', [])
            agent = build_agent(config_state, include_web=include_web)
        except Exception as e:
            logger.error("Failed to build agent", extra={"error": str(e)})
            yield (
                history,
                None,
                f"Failed to initialize agent: {str(e)}",
                gr.update(interactive=True),
                gr.update(visible=False),
                None, None, None, False, None, None, None, None
            )
            return

        # Initialize streaming state
        collected_deltas = []
        start_time = asyncio.get_event_loop().time()

        def on_delta(delta: str) -> None:
            """Accumulate streaming deltas."""
            if delta and not (cancel_event_state and cancel_event_state.is_set()):
                collected_deltas.append(delta)

        # Create new cancel event if none provided
        active_cancel_event = cancel_event_state or Event()

        # Yield initial streaming state
        yield (
            history,
            None,
            "Generating response...",
            gr.update(interactive=False),
            gr.update(visible=True),
            None,
            agent,
            active_cancel_event,
            True,
            experiment_id or "",
            task_label or "",
            run_notes or "",
            None
        )

        # Perform streaming with comprehensive error handling
        try:
            stream_result = await run_agent_stream(
                agent, sanitized_message, on_delta, active_cancel_event,
                correlation_id=correlation_id
            )

            # Check if cancelled during streaming
            if active_cancel_event.is_set() or stream_result.aborted:
                final_text = "".join(collected_deltas)
                status_msg = f"Generation cancelled. Partial response: {len(final_text)} characters."
            else:
                final_text = stream_result.text
                status_msg = "Response ready."

            # Prepare final history
            new_history = history or []
            new_history.append([sanitized_message, final_text])

            # Persist run data
            try:
                run_record = RunRecord(
                    ts=datetime.now(timezone.utc),
                    agent_name=config_state.name,
                    model=config_state.model,
                    prompt_tokens=stream_result.usage.get("prompt_tokens", 0) if stream_result.usage else 0,
                    completion_tokens=stream_result.usage.get("completion_tokens", 0) if stream_result.usage else 0,
                    total_tokens=stream_result.usage.get("total_tokens", 0) if stream_result.usage else 0,
                    latency_ms=stream_result.latency_ms,
                    cost_usd=calculate_cost(config_state.model, stream_result.usage) if stream_result.usage else 0.0,
                    experiment_id=experiment_id or "",
                    task_label=task_label or "",
                    run_notes=run_notes or "",
                    streaming=True,
                    model_list_source=model_source_enum,
                    tool_web_enabled=include_web,
                    web_status="ok" if include_web else "off",
                    aborted=stream_result.aborted
                )
                await persist_run_async(run_record)
            except Exception as e:
                logger.warning("Failed to persist run data", extra={"error": str(e)})
                # Don't fail the UI for persistence errors

            # Final yield with complete state
            yield (
                new_history,
                None,
                status_msg,
                gr.update(interactive=True),
                gr.update(visible=False),
                None,
                None,
                None,
                False,
                experiment_id or "",
                task_label or "",
                run_notes or "",
                {
                    "latency_ms": stream_result.latency_ms,
                    "usage": stream_result.usage,
                    "aborted": stream_result.aborted
                }
            )

        except Exception as e:
            logger.error("Streaming failed", extra={"error": str(e), "correlation_id": correlation_id})
            error_msg = f"Generation failed: {str(e)}"

            # Yield error state
            yield (
                history,
                None,
                error_msg,
                gr.update(interactive=True),
                gr.update(visible=False),
                None, None, None, False, None, None, None, None
            )

    except Exception as e:
        logger.error("Unexpected error in send_message_streaming", extra={"error": str(e)})
        yield (
            history,
            None,
            f"Unexpected error: {str(e)}",
            gr.update(interactive=True),
            gr.update(visible=False),
            None, None, None, False, None, None, None, None
        )
```

### Issue: Loading State Manager Race Conditions
**Problem**: LoadingStateManager doesn't handle concurrent operations properly.

**Fix: Thread-Safe Loading State Manager**

```python
class ThreadSafeLoadingStateManager:
    """
    Thread-safe loading state manager with proper concurrency handling.
    """

    def __init__(self):
        self._states: dict[str, dict] = {}
        self._lock = asyncio.Lock()

    async def start_loading(self, operation_id: str, component: str) -> dict:
        """
        Start loading state for an operation with thread safety.
        """
        async with self._lock:
            if operation_id in self._states:
                # Operation already in progress
                return self._get_current_state(component)

            self._states[operation_id] = {
                "start_time": asyncio.get_event_loop().time(),
                "component": component
            }

            return self._get_loading_state(component)

    async def complete_loading(self, operation_id: str) -> dict:
        """
        Complete loading state for an operation.
        """
        async with self._lock:
            if operation_id not in self._states:
                return self._get_default_state()

            state = self._states.pop(operation_id)
            component = state["component"]

            return self._get_completed_state(component)

    async def cancel_loading(self, operation_id: str) -> dict:
        """
        Cancel loading state for an operation.
        """
        async with self._lock:
            state = self._states.pop(operation_id, None)
            if not state:
                return self._get_default_state()

            component = state["component"]
            return self._get_cancelled_state(component)

    def _get_loading_state(self, component: str) -> dict:
        """Get loading state for component."""
        if component == "button":
            return {"interactive": False, "value": "Processing..."}
        elif component == "panel":
            return {"visible": True, "value": "Loading..."}
        return {}

    def _get_completed_state(self, component: str) -> dict:
        """Get completed state for component."""
        if component == "button":
            return {"interactive": True, "value": "Send Message"}
        elif component == "panel":
            return {"visible": False, "value": ""}
        return {}

    def _get_cancelled_state(self, component: str) -> dict:
        """Get cancelled state for component."""
        if component == "button":
            return {"interactive": True, "value": "Cancelled"}
        elif component == "panel":
            return {"visible": False, "value": "Cancelled"}
        return {}

    def _get_default_state(self) -> dict:
        """Get default state."""
        return {}

    def _get_current_state(self, component: str) -> dict:
        """Get current state for component."""
        return self._get_loading_state(component)
```

## 3. Security Validation Fixes

### Issue: Input Sanitization Edge Cases
**Problem**: validate_agent_name and other validators don't handle Unicode normalization or complex injection patterns.

**Fix: Comprehensive Input Validation**

```python
import unicodedata
import re

def validate_agent_name_comprehensive(name: str) -> dict:
    """
    Comprehensive agent name validation with Unicode and injection protection.

    Handles:
    - Unicode normalization
    - Complex XSS patterns
    - Path traversal attempts
    - SQL injection patterns
    - Length limits
    """
    if not isinstance(name, str):
        return {"is_valid": False, "message": "Name must be a string"}

    # Unicode normalization to catch homoglyph attacks
    normalized_name = unicodedata.normalize('NFKC', name)

    # Length checks
    if len(normalized_name) == 0:
        return {"is_valid": False, "message": "Agent name cannot be empty"}

    if len(normalized_name) > 100:
        return {"is_valid": False, "message": "Agent name cannot exceed 100 characters"}

    # Reject control characters
    if any(ord(c) < 32 for c in normalized_name):
        return {"is_valid": False, "message": "Agent name cannot contain control characters"}

    # XSS patterns (expanded)
    xss_patterns = [
        r'<script[^>]*>.*?</script>',
        r'<iframe[^>]*>.*?</iframe>',
        r'<object[^>]*>.*?</object>',
        r'<embed[^>]*>.*?</embed>',
        r'javascript:',
        r'vbscript:',
        r'data:',
        r'<[^>]*on\w+\s*=',
        r'expression\s*\(',
        r'vbscript\s*:',
        r'onload\s*=',
        r'onerror\s*=',
    ]

    for pattern in xss_patterns:
        if re.search(pattern, normalized_name, re.IGNORECASE):
            return {"is_valid": False, "message": "Agent name contains potentially unsafe content"}

    # SQL injection patterns
    sql_patterns = [
        r';\s*drop\s+',
        r';\s*delete\s+from\s+',
        r';\s*update\s+.*set\s+',
        r'union\s+select\s+',
        r'\bexec\s*\(',
        r'\beval\s*\(',
    ]

    for pattern in sql_patterns:
        if re.search(pattern, normalized_name, re.IGNORECASE):
            return {"is_valid": False, "message": "Agent name contains potentially unsafe content"}

    # Path traversal patterns
    if '..' in normalized_name or '\\' in normalized_name:
        return {"is_valid": False, "message": "Agent name contains invalid path characters"}

    # Valid name pattern (alphanumeric, spaces, hyphens, underscores)
    if not re.match(r'^[a-zA-Z0-9\s\-_]+$', normalized_name):
        return {"is_valid": False, "message": "Agent name can only contain letters, numbers, spaces, hyphens, and underscores"}

    return {"is_valid": True, "message": "Valid agent name"}

def validate_system_prompt_comprehensive(prompt: str) -> dict:
    """
    Comprehensive system prompt validation with content analysis.
    """
    if not isinstance(prompt, str):
        return {"is_valid": False, "message": "System prompt must be a string"}

    # Length limit (reasonable for system prompts)
    if len(prompt) > 10000:
        return {"is_valid": False, "message": "System prompt cannot exceed 10,000 characters"}

    # Check for prompt injection patterns
    injection_patterns = [
        r'ignore\s+all\s+previous\s+instructions',
        r'override\s+system\s+prompt',
        r'system\s+prompt\s+override',
        r'you\s+are\s+no\s+longer',
        r'forget\s+your\s+previous',
        r'\[system\]',
        r'\[override\]',
    ]

    prompt_lower = prompt.lower()
    for pattern in injection_patterns:
        if re.search(pattern, prompt_lower):
            return {"is_valid": False, "message": "System prompt contains potentially unsafe override patterns"}

    # Check for code execution patterns
    code_patterns = [
        r'exec\s*\(',
        r'eval\s*\(',
        r'execfile\s*\(',
        r'__import__\s*\(',
        r'subprocess\.',
        r'os\.system\s*\(',
        r'os\.popen\s*\(',
    ]

    for pattern in code_patterns:
        if re.search(pattern, prompt):
            return {"is_valid": False, "message": "System prompt contains code execution patterns"}

    return {"is_valid": True, "message": "Valid system prompt"}

def validate_temperature_robust(value: Any) -> dict:
    """
    Robust temperature validation with comprehensive type checking.
    """
    # Handle None
    if value is None:
        return {"is_valid": False, "message": "Temperature is required"}

    # Handle string inputs
    if isinstance(value, str):
        try:
            # Remove whitespace
            value = value.strip()
            # Try to convert to float
            numeric_value = float(value)
        except ValueError:
            return {"is_valid": False, "message": "Temperature must be a valid number"}
    elif isinstance(value, (int, float)):
        numeric_value = float(value)
    else:
        return {"is_valid": False, "message": "Temperature must be a number"}

    # Range validation
    if numeric_value < 0.0:
        return {"is_valid": False, "message": "Temperature cannot be less than 0.0"}

    if numeric_value > 2.0:
        return {"is_valid": False, "message": "Temperature cannot be greater than 2.0"}

    # Check for potential issues with extreme precision
    if numeric_value != round(numeric_value, 6):
        return {"is_valid": False, "message": "Temperature precision is too high"}

    return {"is_valid": True, "message": "Valid temperature"}
```

## 4. Session Handling Fixes

### Issue: CSV Persistence Data Type Coercion
**Problem**: _coerce_int, _coerce_float, _coerce_bool functions don't handle edge cases properly.

**Fix: Robust Data Type Coercion**

```python
def _coerce_int_robust(value: str) -> int:
    """
    Robust integer coercion with proper error handling.
    """
    if not value or value.strip() == "":
        return 0

    try:
        # Strip whitespace
        cleaned = value.strip()
        # Handle potential float strings
        if '.' in cleaned:
            return int(float(cleaned))
        return int(cleaned)
    except (ValueError, OverflowError):
        logger.warning(f"Failed to coerce '{value}' to int, defaulting to 0")
        return 0

def _coerce_float_robust(value: str) -> float:
    """
    Robust float coercion with proper error handling.
    """
    if not value or value.strip() == "":
        return 0.0

    try:
        cleaned = value.strip()
        return float(cleaned)
    except (ValueError, OverflowError):
        logger.warning(f"Failed to coerce '{value}' to float, defaulting to 0.0")
        return 0.0

def _coerce_bool_robust(value: str) -> bool:
    """
    Robust boolean coercion with comprehensive truthy/falsy handling.
    """
    if not value:
        return False

    cleaned = value.strip().lower()

    # Truthy values
    if cleaned in ('true', '1', 'yes', 'on', 'enabled'):
        return True

    # Falsy values
    if cleaned in ('false', '0', 'no', 'off', 'disabled', ''):
        return False

    # Default to False for unrecognized values
    logger.warning(f"Unrecognized boolean value '{value}', defaulting to False")
    return False

def _parse_row_robust(row: dict[str, str]) -> RunRecord | None:
    """
    Robust row parsing with comprehensive error handling.
    """
    try:
        # Required fields validation
        ts_str = row.get('ts', '').strip()
        if not ts_str:
            logger.warning("Missing timestamp in row, skipping")
            return None

        try:
            ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
        except ValueError:
            logger.warning(f"Invalid timestamp format '{ts_str}', skipping")
            return None

        # Extract and coerce all fields
        agent_name = row.get('agent_name', '').strip()
        model = row.get('model', '').strip()

        # All numeric fields with robust coercion
        prompt_tokens = _coerce_int_robust(row.get('prompt_tokens', '0'))
        completion_tokens = _coerce_int_robust(row.get('completion_tokens', '0'))
        total_tokens = _coerce_int_robust(row.get('total_tokens', '0'))
        latency_ms = _coerce_int_robust(row.get('latency_ms', '0'))
        cost_usd = _coerce_float_robust(row.get('cost_usd', '0.0'))

        # String fields with defaults
        experiment_id = row.get('experiment_id', '').strip()
        task_label = row.get('task_label', '').strip()
        run_notes = row.get('run_notes', '').strip()
        model_list_source = row.get('model_list_source', 'unknown').strip()
        web_status = row.get('web_status', 'off').strip()

        # Boolean fields
        streaming = _coerce_bool_robust(row.get('streaming', 'false'))
        tool_web_enabled = _coerce_bool_robust(row.get('tool_web_enabled', 'false'))
        aborted = _coerce_bool_robust(row.get('aborted', 'false'))

        return RunRecord(
            ts=ts,
            agent_name=agent_name,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            latency_ms=latency_ms,
            cost_usd=cost_usd,
            experiment_id=experiment_id,
            task_label=task_label,
            run_notes=run_notes,
            streaming=streaming,
            model_list_source=model_list_source,
            tool_web_enabled=tool_web_enabled,
            web_status=web_status,
            aborted=aborted
        )

    except Exception as e:
        logger.error(f"Failed to parse row: {e}", extra={"row": row})
        return None
```

### Issue: Session Load/Save Race Conditions
**Problem**: Concurrent session operations can corrupt data.

**Fix: Atomic Session Operations**

```python
async def save_session_atomic(
    session_name: str,
    config: AgentConfig,
    history: list[list[str]],
    session_dir: Path
) -> Session:
    """
    Atomically save session with proper error handling and validation.
    """
    if not session_name or not session_name.strip():
        raise ValueError("Session name cannot be empty")

    if not history:
        raise ValueError("Session history cannot be empty")

    # Create session object
    session = Session(
        id=str(uuid.uuid4()),
        created_at=datetime.now(timezone.utc),
        agent_config=config,
        transcript=[
            {
                "role": "user" if i % 2 == 0 else "assistant",
                "content": msg,
                "ts": datetime.now(timezone.utc).isoformat()
            }
            for conversation in history
            for i, msg in enumerate(conversation)
        ],
        model_id=config.model
    )

    # Atomic write using temporary file
    session_file = session_dir / f"{session.id}.json"
    temp_file = session_file.with_suffix('.tmp')

    try:
        # Write to temporary file first
        async with aiofiles.open(temp_file, 'w', encoding='utf-8') as f:
            await f.write(session.model_dump_json(indent=2))

        # Atomic move to final location
        temp_file.replace(session_file)

        logger.info("Session saved successfully", extra={
            "session_id": session.id,
            "session_name": session_name
        })

        return session

    except Exception as e:
        # Clean up temp file on failure
        if temp_file.exists():
            temp_file.unlink()
        logger.error("Failed to save session", extra={"error": str(e)})
        raise

async def load_session_atomic(session_id: str, session_dir: Path) -> Session:
    """
    Atomically load session with validation.
    """
    session_file = session_dir / f"{session_id}.json"

    if not session_file.exists():
        raise FileNotFoundError(f"Session {session_id} not found")

    try:
        async with aiofiles.open(session_file, 'r', encoding='utf-8') as f:
            content = await f.read()

        session = Session.model_validate_json(content)

        # Validate session integrity
        if not session.transcript:
            raise ValueError("Session has no transcript")

        logger.info("Session loaded successfully", extra={
            "session_id": session.id,
            "transcript_length": len(session.transcript)
        })

        return session

    except Exception as e:
        logger.error("Failed to load session", extra={
            "session_id": session_id,
            "error": str(e)
        })
        raise
```

## 5. Content Truncation Fixes

### Issue: Content Truncation Without Encoding Awareness
**Problem**: fetch_url truncates bytes without considering character encoding.

**Fix: Encoding-Aware Content Truncation**

```python
async def fetch_url_encoding_aware(
    ctx: RunContext,
    input: FetchInput
) -> str:
    """
    Fetch URL content with encoding-aware truncation.

    Properly handles:
    - Character encoding detection
    - Safe truncation at character boundaries
    - Content length limits
    """
    try:
        parsed_url = urlparse(input.url)
        domain = parsed_url.netloc.lower()

        if domain not in ALLOWED_DOMAINS:
            return f"Refused: domain '{domain}' not in allow-list."

        async with httpx.AsyncClient(
            timeout=input.timeout_s,
            follow_redirects=True,
            headers={'User-Agent': 'Agent-Lab/1.0'}
        ) as client:
            response = await client.get(input.url)
            response.raise_for_status()

            # Get content with encoding detection
            content = response.text

            # Check if truncation is needed
            if len(content) <= 4096:
                return content

            # Truncate at character boundary, not byte boundary
            truncated = content[:4096]

            # Ensure we don't cut in the middle of a multi-byte character
            try:
                # Try to encode and decode to validate UTF-8
                truncated.encode('utf-8').decode('utf-8')
                return truncated + "\n\n[Content truncated to 4096 characters]"
            except UnicodeDecodeError:
                # If encoding fails, truncate more conservatively
                safe_truncate = content[:4090]  # Leave room for truncation message
                # Find last complete character
                while safe_truncate and len(safe_truncate.encode('utf-8')) > 4080:
                    safe_truncate = safe_truncate[:-1]

                return safe_truncate + "\n\n[Content truncated]"

    except httpx.TimeoutException:
        return "Error: Request timed out."
    except httpx.HTTPStatusError as e:
        return f"Error: HTTP {e.response.status_code} - {e.response.reason_phrase}"
    except UnicodeDecodeError:
        return "Error: Failed to decode response content."
    except Exception as e:
        return f"Error: {str(e)}"
```

### Issue: Content Type Validation
**Problem**: fetch_url doesn't validate content types, allowing binary content.

**Fix: Content Type Validation**

```python
ALLOWED_CONTENT_TYPES = {
    'text/plain',
    'text/html',
    'text/xml',
    'application/json',
    'application/xml',
    'application/rss+xml',
    'text/markdown',
    'text/x-markdown'
}

def is_allowed_content_type(content_type: str) -> bool:
    """
    Check if content type is allowed for text processing.
    """
    if not content_type:
        return False

    # Extract main type/subtype
    main_type = content_type.split(';')[0].strip().lower()

    # Allow text/* and specific application types
    if main_type.startswith('text/'):
        return True

    return main_type in ALLOWED_CONTENT_TYPES

async def fetch_url_with_content_validation(
    ctx: RunContext,
    input: FetchInput
) -> str:
    """
    Fetch URL with content type validation and encoding-aware truncation.
    """
    try:
        parsed_url = urlparse(input.url)
        domain = parsed_url.netloc.lower()

        if domain not in ALLOWED_DOMAINS:
            return f"Refused: domain '{domain}' not in allow-list."

        async with httpx.AsyncClient(
            timeout=input.timeout_s,
            follow_redirects=True,
            headers={'User-Agent': 'Agent-Lab/1.0'}
        ) as client:
            response = await client.get(input.url)
            response.raise_for_status()

            # Validate content type
            content_type = response.headers.get('content-type', '').lower()
            if not is_allowed_content_type(content_type):
                return f"Error: Unsupported content type '{content_type}'"

            # Detect encoding
            detected_encoding = response.encoding or 'utf-8'

            try:
                content = response.text
            except UnicodeDecodeError:
                return "Error: Failed to decode response as text."

            # Apply size limits
            if len(content) > 4096:
                content = content[:4096]
                content += "\n\n[Content truncated to 4096 characters]"

            return content

    except httpx.TimeoutException:
        return "Error: Request timed out."
    except httpx.HTTPStatusError as e:
        return f"Error: HTTP {e.response.status_code} - {e.response.reason_phrase}"
    except Exception as e:
        return f"Error: {str(e)}"