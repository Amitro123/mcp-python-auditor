def run_duplication(path: Path) -> dict:
    """Find code duplication using a robust 6-line block hashing."""
    import hashlib
    try:
        py_files = list(Path(path).glob("**/*.py"))
        hashes = {} # hash -> list of (file, start_line)
        
        # Limit to 1000 files to avoid performance hit
        files_to_scan = py_files[:1000]
        
        for f in files_to_scan: 
            try:
                # Read file
                with open(f, 'r', encoding='utf-8', errors='ignore') as fp:
                    lines = fp.readlines()
                
                # Normalize lines (ignore empty and comments)
                clean_lines = []
                for i, l in enumerate(lines):
                    stripped = l.strip()
                    if stripped and not stripped.startswith('#'):
                        clean_lines.append((i+1, stripped)) # 1-based index
                
                # Sliding window of 6 lines
                if len(clean_lines) < 6: continue
                
                for i in range(len(clean_lines) - 5):
                     # Create window string
                     window = "".join([x[1] for x in clean_lines[i:i+6]])
                     h = hashlib.md5(window.encode('utf-8')).hexdigest()
                     
                     if h not in hashes: hashes[h] = []
                     hashes[h].append((str(f.relative_to(path)), clean_lines[i][0]))
            except: pass
            
        duplicates = []
        for h, locs in hashes.items():
            if len(locs) > 1:
                # locs is list of (file, line)
                files_involved = list(set([l[0] for l in locs]))
                # Only count substantial duplication (more than 1 occurrence)
                duplicates.append({
                     "hash": h, 
                     "count": len(locs), 
                     "files": files_involved[:5], 
                     "locations": [f"{l[0]}:{l[1]}" for l in locs[:5]]
                })
        
        # Sort by count desc
        duplicates.sort(key=lambda x: x['count'], reverse=True)
        
        return {
            "tool": "duplication",
            "status": "issues_found" if duplicates else "clean",
            "total_duplicates": len(duplicates),
            "duplicates": duplicates[:10]
        }
    except Exception as e:
         return {"tool": "duplication", "status": "error", "error": str(e)}
