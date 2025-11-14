#!/usr/bin/env python3
"""
Fix ALL .is_alive() calls in ALL Python files in the addon
"""
import os
import sys

def fix_file(filepath):
    """Fix isAlive in a single file"""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        count = content.count('.is_alive()')
        if count == 0:
            return 0
        
        # Replace
        content = content.replace('.is_alive()', '.is_alive()')
        
        # Write back
        with open(filepath, 'w', encoding='utf-8', newline='') as f:
            f.write(content)
        
        print(f"  ✓ Fixed {count} in {os.path.basename(filepath)}")
        return count
    except Exception as e:
        print(f"  ✗ Error in {filepath}: {e}")
        return 0

def main():
    addon_path = input("Enter addon directory path: ").strip() or "."
    
    if not os.path.isdir(addon_path):
        print(f"Error: '{addon_path}' is not a directory")
        return 1
    
    print("=" * 70)
    print("Fixing ALL .is_alive() → .is_alive() in addon")
    print("=" * 70)
    print(f"Path: {addon_path}")
    print()
    
    total_fixed = 0
    files_fixed = 0
    
    for root, dirs, files in os.walk(addon_path):
        # Skip hidden dirs
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
        
        for filename in files:
            if filename.endswith('.py'):
                filepath = os.path.join(root, filename)
                count = fix_file(filepath)
                if count > 0:
                    files_fixed += 1
                    total_fixed += count
    
    print()
    print("=" * 70)
    print(f"COMPLETE: Fixed {total_fixed} occurrences in {files_fixed} files")
    print("=" * 70)
    return 0

if __name__ == '__main__':
    sys.exit(main())
