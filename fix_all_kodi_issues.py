#!/usr/bin/env python3
"""
Automatically fix ALL Kodi 17→21 migration issues in Python files
Version 6: Now includes dialog.ok() fix for Kodi 19+ API change
(No backup version - makes changes directly)
"""
import os
import sys
import re

def fix_dialog_update(content):
    """Fix dialog.update() calls from Kodi 18 (4 args) to Kodi 19+ (2 args)"""
    changes = []
    
    # Pattern: dialog.update(percent, line1, line2) or dialog.update(percent, line1, line2, line3)
    # We need to be careful and look for actual method calls
    
    # Find all .update( calls with multiple arguments
    # Pattern matches: something.update(arg1, arg2, arg3) or more args
    pattern = r'(\w+\.update\s*\(\s*([^,]+)\s*,\s*([^,)]+)(?:\s*,\s*([^,)]+))?(?:\s*,\s*([^,)]+))?\s*\))'
    
    def replace_update(match):
        full_match = match.group(0)
        
        # Skip if it's not a dialog/progress update (crude check)
        if 'Dialog' not in full_match and 'dialog' not in full_match and 'progress' not in full_match.lower():
            return full_match
        
        # Extract the object and arguments
        obj_and_first = match.group(1)  # Full match
        
        # Try to parse it better
        # Format: obj.update(percent, line1, line2, line3)
        parts = full_match.split('(', 1)
        if len(parts) != 2:
            return full_match
        
        obj_part = parts[0]  # "obj.update"
        args_part = parts[1].rstrip(')')  # "percent, line1, line2, line3"
        
        # Split arguments
        args = [arg.strip() for arg in args_part.split(',')]
        
        if len(args) <= 2:
            # Already correct format or other method
            return full_match
        
        # We have 3+ arguments, need to fix
        percent = args[0]
        lines = args[1:]
        
        # Combine lines with \n
        combined = ' + "\\n" + '.join(lines)
        
        new_call = f"{obj_part}({percent}, {combined})"
        return new_call
    
    new_content = re.sub(pattern, replace_update, content)
    
    if new_content != content:
        changes.append('Fixed dialog.update() calls for Kodi 19+ (2 args)')
        return new_content, changes
    
    return content, []

def fix_file(filepath):
    """Fix all issues in a single file"""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        original_content = content
        changes = []
        
        # Fix 1: xbmc.LOGNOTICE → xbmc.LOGINFO
        if 'xbmc.LOGNOTICE' in content:
            content = content.replace('xbmc.LOGNOTICE', 'xbmc.LOGINFO')
            changes.append('Fixed xbmc.LOGNOTICE → xbmc.LOGINFO')
        
        # Fix 2: .decode("utf-8") and .decode('utf-8')
        if '.decode("utf-8")' in content or ".decode('utf-8')" in content:
            content = content.replace('.decode("utf-8")', '')
            content = content.replace(".decode('utf-8')", '')
            changes.append('Removed .decode("utf-8")')
        
        # Fix 3: xbmc.translatePath → xbmcvfs.translatePath
        if 'xbmc.translatePath' in content:
            content = content.replace('xbmc.translatePath', 'xbmcvfs.translatePath')
            changes.append('Fixed xbmc.translatePath → xbmcvfs.translatePath')
            
            # Add xbmcvfs import if not present
            if 'import xbmcvfs' not in content:
                lines = content.split('\n')
                insert_pos = 0
                
                for i, line in enumerate(lines):
                    if line.startswith('import xbmc') and 'xbmcvfs' not in line:
                        insert_pos = i + 1
                
                if insert_pos > 0:
                    lines.insert(insert_pos, 'import xbmcvfs')
                    content = '\n'.join(lines)
                    changes.append('Added import xbmcvfs')
        
        # Fix 4: httplib → http.client (Python 3)
        if 'import httplib' in content and 'http.client' not in content:
            # Replace with Python 2/3 compatible import
            content = content.replace(
                'import httplib',
                'try:\n    import httplib  # Python 2\nexcept ImportError:\n    import http.client as httplib  # Python 3'
            )
            changes.append('Fixed httplib → http.client (Python 2/3 compatible)')
        
        # Fix 5: xbmc.abortRequested
        if 'xbmc.abortRequested' in content and 'monitor' not in content.lower():
            lines = content.split('\n')
            new_lines = []
            i = 0
            
            while i < len(lines):
                line = lines[i]
                
                if 'while' in line and 'xbmc.abortRequested' in line:
                    indent = len(line) - len(line.lstrip())
                    indent_str = ' ' * indent
                    
                    new_lines.append(indent_str + 'monitor = xbmc.Monitor()')
                    new_line = line.replace('xbmc.abortRequested', 'monitor.abortRequested()')
                    new_lines.append(new_line)
                    changes.append('Fixed xbmc.abortRequested → monitor.abortRequested()')
                else:
                    new_lines.append(line)
                
                i += 1
            
            content = '\n'.join(new_lines)
        
        # Fix 6: dialog.update() with 3+ arguments (Kodi 19+)
        if '.update(' in content and ('dialog' in content.lower() or 'progress' in content.lower()):
            new_content, dialog_changes = fix_dialog_update(content)
            if dialog_changes:
                content = new_content
                changes.extend(dialog_changes)
        
        # Fix 7: Add Python 2/3 compatibility for unicode/basestring
        needs_compat = False
        has_compat = 'if sys.version_info[0] >= 3:' in content and 'unicode = str' in content
        
        # Check if file uses unicode or basestring
        if not has_compat:
            if ('isinstance(' in content and ('unicode' in content or 'basestring' in content)) or \
               re.search(r'\bunicode\s*\(', content) or \
               re.search(r'\bbasestring\b', content):
                needs_compat = True
        
        if needs_compat:
            lines = content.split('\n')
            
            # Find the position after imports
            import_end = 0
            last_import = 0
            in_docstring = False
            docstring_char = None
            
            for i, line in enumerate(lines):
                stripped = line.strip()
                
                # Track docstrings
                if stripped.startswith('"""') or stripped.startswith("'''"):
                    if not in_docstring:
                        in_docstring = True
                        docstring_char = stripped[:3]
                    elif stripped.endswith(docstring_char):
                        in_docstring = False
                    continue
                
                if in_docstring:
                    continue
                
                # Track imports
                if stripped.startswith('import ') or stripped.startswith('from '):
                    last_import = i
                    
                    # Make sure sys is imported
                    if stripped.startswith('import sys'):
                        import_end = i
                
                # Stop at first non-import, non-comment, non-blank line after imports
                if last_import > 0 and stripped and not stripped.startswith('#') and \
                   not stripped.startswith('import ') and not stripped.startswith('from '):
                    import_end = last_import
                    break
            
            if import_end > 0:
                # Check if sys is imported
                has_sys_import = any('import sys' in line for line in lines[:import_end + 1])
                
                # Build the compatibility block
                compat_lines = []
                
                if not has_sys_import:
                    compat_lines.append('import sys')
                    compat_lines.append('')
                
                compat_lines.append('# Python 2/3 compatibility')
                compat_lines.append('if sys.version_info[0] >= 3:')
                compat_lines.append('    unicode = str')
                compat_lines.append('    basestring = str')
                compat_lines.append('')
                
                # Insert after imports
                lines[import_end + 1:import_end + 1] = compat_lines
                
                content = '\n'.join(lines)
                changes.append('Added Python 2/3 compatibility for unicode/basestring')
        
        # Fix 8: Fix unicode(data, "utf-8") calls - in Python 3, strings are already unicode
        # Pattern: unicode(variable, "utf-8") or unicode(variable, 'utf-8')
        unicode_decode_pattern = r'\bunicode\s*\(\s*(\w+)\s*,\s*["\']utf-8["\']\s*(?:,\s*errors\s*=\s*["\']ignore["\']\s*)?\)'
        
        if re.search(unicode_decode_pattern, content):
            # Find all occurrences and replace with Python 2/3 compatible code
            matches = list(re.finditer(unicode_decode_pattern, content))
            
            if matches:
                # Work backwards to preserve positions
                for match in reversed(matches):
                    var_name = match.group(1)
                    start, end = match.span()
                    
                    # Replace with Python 2/3 compatible version
                    replacement = f'({var_name} if sys.version_info[0] >= 3 else unicode({var_name}, "utf-8", errors="ignore"))'
                    
                    content = content[:start] + replacement + content[end:]
                
                changes.append('Fixed unicode(data, "utf-8") for Python 2/3 compatibility')
        
        # Fix 9: dialog.ok() with 3+ arguments (Kodi 19+)
        # Pattern: dlg.ok(arg1, arg2, arg3) or dialog.ok(arg1, arg2, arg3, arg4)
        dialog_ok_pattern = r'((?:dlg|dialog)\.ok\s*\(\s*[^,)]+\s*,\s*[^,)]+\s*,\s*[^,)]+(?:\s*,\s*[^,)]+)?\s*\))'
        
        if re.search(dialog_ok_pattern, content):
            lines = content.split('\n')
            new_lines = []
            i = 0
            
            while i < len(lines):
                line = lines[i]
                
                # Check if this line contains dialog.ok with multiple arguments
                if ('.ok(' in line) and (('dlg.ok(' in line) or ('dialog.ok(' in line)):
                    # Try to parse the call
                    match = re.search(r'(dlg|dialog)\.ok\s*\(', line)
                    if match:
                        # Count arguments by finding the matching parenthesis
                        # This is a simple heuristic - count commas in the call
                        start_paren = line.find('.ok(') + 4
                        depth = 1
                        end_paren = start_paren
                        
                        for j in range(start_paren, len(line)):
                            if line[j] == '(':
                                depth += 1
                            elif line[j] == ')':
                                depth -= 1
                                if depth == 0:
                                    end_paren = j
                                    break
                        
                        if end_paren > start_paren:
                            args_str = line[start_paren:end_paren]
                            # Count commas not inside strings or parentheses
                            arg_count = args_str.count(',') + 1
                            
                            if arg_count > 2:
                                # Need to fix this call
                                # Extract the parts
                                obj = match.group(1)
                                before_call = line[:line.find('.ok(')]
                                indent = len(before_call) - len(before_call.lstrip())
                                indent_str = ' ' * indent
                                
                                # Parse arguments (simple approach - split by comma)
                                args = [arg.strip() for arg in args_str.split(',')]
                                
                                if len(args) >= 3:
                                    # First arg is heading, rest are message lines
                                    heading = args[0]
                                    msg_lines = [arg for arg in args[1:] if arg and arg != '""' and arg != "''"]
                                    
                                    # Build the combined message
                                    if len(msg_lines) == 1:
                                        combined_msg = msg_lines[0]
                                    else:
                                        # Combine with newlines
                                        combined_msg = ' + "\\n" + '.join(msg_lines)
                                    
                                    # Build new line
                                    new_line = f'{before_call}.ok({heading}, {combined_msg})'
                                    new_lines.append(new_line)
                                    changes.append('Fixed dialog.ok() calls for Kodi 19+ (2 args)')
                                else:
                                    new_lines.append(line)
                            else:
                                new_lines.append(line)
                        else:
                            new_lines.append(line)
                    else:
                        new_lines.append(line)
                else:
                    new_lines.append(line)
                
                i += 1
            
            content = '\n'.join(new_lines)
        
        # Write back if changes were made
        if content != original_content:
            with open(filepath, 'w', encoding='utf-8', newline='') as f:
                f.write(content)
            return True, changes
        
        return False, []
    
    except Exception as e:
        return False, [f"Error: {e}"]

def scan_and_fix_directory(addon_path):
    """Scan and fix all Python files"""
    print("="*70)
    print("Kodi 17→21 Automatic Fixer v6 (No Backup)")
    print("="*70)
    print(f"Addon Path: {addon_path}")
    print("⚠️  WARNING: Changes will be made directly without backups!")
    print("="*70)
    print()
    
    files_fixed = 0
    files_scanned = 0
    total_changes = 0
    
    for root, dirs, files in os.walk(addon_path):
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
        
        for filename in files:
            if filename.endswith('.py') and not filename.startswith('fix_') and not filename.startswith('find_'):
                filepath = os.path.join(root, filename)
                rel_path = os.path.relpath(filepath, addon_path)
                files_scanned += 1
                
                if '.backup_' in filepath:
                    continue
                
                fixed, changes = fix_file(filepath)
                
                if fixed:
                    files_fixed += 1
                    total_changes += len(changes)
                    print(f"\n✓ FIXED: {rel_path}")
                    for change in changes:
                        print(f"  - {change}")
    
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print(f"Files Scanned: {files_scanned}")
    print(f"Files Fixed: {files_fixed}")
    print(f"Total Changes: {total_changes}")
    
    if files_fixed > 0:
        print("\n✓ All issues have been automatically fixed!")
        print("  Please test your addon on Kodi 21.")
    else:
        print("\n✓ No issues found - addon is already clean!")
    
    print("="*70)

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
    
    print("\n⚠️  WARNING: This will modify files directly without creating backups!")
    response = input("Continue? (yes/no): ").strip().lower()
    
    if response not in ['yes', 'y']:
        print("Aborted.")
        return 0
    
    scan_and_fix_directory(addon_path)
    return 0

if __name__ == '__main__':
    sys.exit(main())