from audit import ALL_TOOLS, TOOLS, SLOW_TOOLS

print(f"ALL_TOOLS len: {len(ALL_TOOLS)}")
print(f"ALL_TOOLS content: {ALL_TOOLS}")

# Check for duplicates
seen = set()
dupes = []
for t in ALL_TOOLS:
    if t in seen:
        dupes.append(t)
    seen.add(t)

if dupes:
    print(f"DUPLICATES FOUND: {dupes}")
else:
    print("No duplicates in ALL_TOOLS")

# Check logic for tools_to_run
skip = set() # Empty skip (Full audit)
tools_to_run = [t for t in ALL_TOOLS if t not in skip]
print(f"tools_to_run (Full): {tools_to_run}")

skip_fast = SLOW_TOOLS
tools_to_run_fast = [t for t in ALL_TOOLS if t not in skip_fast]
print(f"tools_to_run (Fast): {tools_to_run_fast}")
