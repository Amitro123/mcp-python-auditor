"""Validate audit dataset for fine-tuning."""
import json
from pathlib import Path
from typing import List, Dict, Any

def validate_dataset(dataset_path: Path) -> Dict[str, Any]:
    """Validate dataset format and content."""
    
    if not dataset_path.exists():
        return {"valid": False, "error": f"Dataset not found: {dataset_path}"}
    
    examples = []
    errors = []
    
    # Load and validate each example
    with open(dataset_path, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f, 1):
            try:
                example = json.loads(line)
                
                # Check required fields
                if "instruction" not in example:
                    errors.append(f"Line {i}: Missing 'instruction' field")
                if "output" not in example:
                    errors.append(f"Line {i}: Missing 'output' field")
                
                # Check field types
                if not isinstance(example.get("instruction"), str):
                    errors.append(f"Line {i}: 'instruction' must be string")
                if not isinstance(example.get("output"), str):
                    errors.append(f"Line {i}: 'output' must be string")
                
                # Check lengths
                if len(example.get("instruction", "")) < 10:
                    errors.append(f"Line {i}: 'instruction' too short")
                if len(example.get("output", "")) < 20:
                    errors.append(f"Line {i}: 'output' too short")
                
                examples.append(example)
                
            except json.JSONDecodeError as e:
                errors.append(f"Line {i}: Invalid JSON - {e}")
    
    # Calculate statistics
    stats = {
        "total_examples": len(examples),
        "avg_instruction_length": sum(len(e["instruction"]) for e in examples) / len(examples) if examples else 0,
        "avg_output_length": sum(len(e["output"]) for e in examples) / len(examples) if examples else 0,
        "min_instruction_length": min(len(e["instruction"]) for e in examples) if examples else 0,
        "max_instruction_length": max(len(e["instruction"]) for e in examples) if examples else 0,
        "min_output_length": min(len(e["output"]) for e in examples) if examples else 0,
        "max_output_length": max(len(e["output"]) for e in examples) if examples else 0,
    }
    
    # Check for duplicates
    instructions = [e["instruction"] for e in examples]
    duplicates = len(instructions) - len(set(instructions))
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "stats": stats,
        "duplicates": duplicates,
        "examples": examples[:3]  # Show first 3 examples
    }

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        dataset_path = Path(sys.argv[1])
    else:
        dataset_path = Path("data/audit_dataset.jsonl")
    
    print("🔍 Validating audit dataset...")
    print(f"📁 Path: {dataset_path}")
    print()
    
    result = validate_dataset(dataset_path)
    
    if result["valid"]:
        print("✅ Dataset is valid!")
        print()
        print("📊 Statistics:")
        for key, value in result["stats"].items():
            if "length" in key:
                print(f"   - {key}: {value:.0f} chars")
            else:
                print(f"   - {key}: {value}")
        
        if result["duplicates"] > 0:
            print(f"\n⚠️  Found {result['duplicates']} duplicate instructions")
        
        print("\n📝 Sample Examples:")
        for i, example in enumerate(result["examples"], 1):
            print(f"\n   Example {i}:")
            print(f"   Instruction: {example['instruction'][:80]}...")
            print(f"   Output: {example['output'][:80]}...")
    else:
        print("❌ Dataset validation failed!")
        print("\n🐛 Errors:")
        for error in result["errors"][:10]:  # Show first 10 errors
            print(f"   - {error}")
        
        if len(result["errors"]) > 10:
            print(f"   ... and {len(result['errors']) - 10} more errors")
    
    print("\n" + "="*60)
    print(f"Total: {result['stats']['total_examples']} examples")
    print(f"Status: {'PASS ✅' if result['valid'] else 'FAIL ❌'}")
