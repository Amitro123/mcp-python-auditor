import re
import os

path = r'c:\Users\USER\.gemini\antigravity\playground\chrono-meteoroid\backend\coverage_raw.txt'
if os.path.exists(path):
    # Try multiple encodings
    for encoding in ['utf-8', 'utf-16', 'cp1252']:
        try:
            with open(path, 'r', encoding=encoding) as f:
                data = f.read()
            print(f"Read with {encoding}")
            break
        except:
            continue
    else:
        with open(path, 'r', errors='ignore') as f:
            data = f.read()
        print("Read with errors ignored")
    
    for line in data.split('\n'):
        if 'TOTAL' in line:
            print(f"Checking line: '{line}'")
            match = re.search(r'TOTAL\s+.*?(\d+)%', line)
            if match:
                print(f"Matched: {match.group(1)}")
            else:
                print("No match")
else:
    print("File not found")
