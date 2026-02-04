# Testing Guide

## Quick Test
```bash
pytest tests/ -v
```

## Key Test Patterns

**Tool Test**:
```python
async def test_tool(tmp_path):
    file = tmp_path / "test.py"
    file.write_text("import pickle\npickle.loads(x)")
    
    tool = BanditTool()
    result = await tool.run([file])
    
    assert result.issues_found > 0
```

**Cache Test**:
```python
def test_cache_hit(cache_manager, files):
    cache_manager.set("key", files, {"data": "value"})
    assert cache_manager.is_valid("key", files)
```

## Performance Test
```bash
time python audit.py . --fast  # Should be <10s
```
