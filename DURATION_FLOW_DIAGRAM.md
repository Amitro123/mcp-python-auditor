# Duration Flow Diagram

## How Duration Travels Through the System

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. AUDIT START (mcp_fastmcp_server.py:1151)                    │
│    JOBS[job_id] = {"start_time": time.time()}                  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. TOOLS EXECUTE IN PARALLEL (Lines 1171-1184)                 │
│    Each tool gets duration_s added to its result               │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. CALCULATE TOTAL DURATION (Lines 1186-1187)                  │
│    duration = f"{time.time() - start_time:.2f}s"  (string)     │
│    duration_seconds = time.time() - start_time    (numeric)    │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. ADD TO RESULT_DICT (Line 1203)                              │
│    result_dict = {                                              │
│        "bandit": ...,                                           │
│        "tests": ...,                                            │
│        "duration_seconds": duration_seconds  ← ADDED            │
│    }                                                            │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ 5. PASS TO REPORT GENERATOR (Line 1214)                        │
│    generator.generate_report(                                  │
│        tool_results=result_dict  ← Contains duration_seconds   │
│    )                                                            │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ 6. EXTRACT IN REPORT_GENERATOR_V2 (Lines 137-145)              │
│    duration = tool_results.get('duration_seconds')             │
│    if isinstance(duration, str):                               │
│        duration = float(duration.rstrip('s'))                  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ 7. PASS TO BUILD_REPORT_CONTEXT (Line 148)                     │
│    context = build_report_context(                             │
│        duration=duration  ← Numeric value (e.g., 12.5)         │
│    )                                                            │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ 8. FORMAT IN REPORT_CONTEXT (Line 66)                          │
│    'duration': f"{duration:.2f}s" if duration else "N/A"       │
│    Result: "12.50s"                                             │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ 9. AVAILABLE IN TEMPLATE                                       │
│    {{ duration }}  → Displays "12.50s"                         │
└─────────────────────────────────────────────────────────────────┘
```

## Key Points

1. **Start Time**: Captured when audit job begins
2. **Tool Duration**: Each tool tracks its own execution time (`duration_s`)
3. **Total Duration**: Calculated as difference between end and start time
4. **Dual Format**: Stored as both string ("12.34s") and numeric (12.34)
5. **Numeric in result_dict**: Ensures report generator can parse it
6. **String Parsing**: Handles both formats gracefully
7. **Template Display**: Formatted consistently as "X.XXs"

## Example Values at Each Stage

| Stage | Variable | Value | Type |
|-------|----------|-------|------|
| 1. Start | `start_time` | `1737537600.0` | float |
| 3. Calculate | `duration` | `"12.34s"` | str |
| 3. Calculate | `duration_seconds` | `12.34` | float |
| 4. Store | `result_dict['duration_seconds']` | `12.34` | float |
| 6. Extract | `duration` | `12.34` | float |
| 8. Format | `context['duration']` | `"12.34s"` | str |
| 9. Display | `{{ duration }}` | `"12.34s"` | str |
