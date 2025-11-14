#!/usr/bin/env python3
"""
Search for sys.setcheckinterval usage in Kodi addon files
"""
import os
import sys

def search_for_setcheckinterval(addon_path):
    """Search all Python files for setcheckinterval usage"""
    print("=" * 70)
    print("Searching for sys.setcheckinterval in addon files")
    print("=" * 70)
    print(f"Addon Path: {addon_path}")
    print()
    
    found_files = []
    total_files = 0
    
    for root, dirs, files in os.walk(addon_path):
        # Skip hidden directories and common exclude patterns
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__' and d != '.git']
        
        for filename in files:
            if filename.endswith('.py'):
                total_files += 1
                filepath = os.path.join(root, filename)
                rel_path = os.path.relpath(filepath, addon_path)
                
                try:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = f.readlines()
                    
                    # Search for setcheckinterval in each line
                    for line_num, line in enumerate(lines, 1):
                        if 'setcheckinterval' in line:
                            found_files.append({
                                'file': rel_path,
                                'line': line_num,
                                'content': line.strip()
                            })
                            
                except Exception as e:
                    print(f"Error reading {rel_path}: {e}")
    
    print(f"Scanned {total_files} Python files")
    print()
    
    if found_files:
        print("=" * 70)
        print(f"FOUND {len(found_files)} occurrence(s) of setcheckinterval:")
        print("=" * 70)
        
        for item in found_files:
            print(f"\nFile: {item['file']}")
            print(f"Line: {item['line']}")
            print(f"Code: {item['content']}")
            print(f"Full Path: {os.path.join(addon_path, item['file'])}")
        
        print("\n" + "=" * 70)
        print("FIX NEEDED:")
        print("=" * 70)
        print("Replace 'sys.setcheckinterval' with Python 2/3 compatible code:")
        print()
        print("# Python 2/3 compatibility")
        print("if sys.version_info[0] >= 3:")
        print("    sys.setswitchinterval(0.005)")
        print("else:")
        print("    sys.setcheckinterval(100)")
        print("=" * 70)
        
    else:
        print("=" * 70)
        print("NO occurrences of 'setcheckinterval' found!")
        print("=" * 70)
        print()
        print("This is strange. The error might be coming from:")
        print("1. A compiled .pyc file")
        print("2. An imported external library")
        print("3. Code that was already modified")
        print()
        print("Check the Kodi log for the full traceback to see the exact file.")
    
    return found_files

def main():
    if len(sys.argv) > 1:
        addon_path = sys.argv[1]
    else:
        addon_path = input("Enter addon directory path (or press Enter for current directory): ").strip()
        if not addon_path:
            addon_path = '.'
    
    if not os.path.isdir(addon_path):
        print(f"Error: '{addon_path}' is not a valid directory")
        return 1
    
    search_for_setcheckinterval(addon_path)
    return 0

if __name__ == '__main__':
    sys.exit(main())
