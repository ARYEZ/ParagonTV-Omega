#!/usr/bin/env python3
"""
Complete Kodi Addon Directory Converter
Converts entire addon from Python 2.7 to Python 3

Usage:
    python3 convert_complete_addon.py /path/to/addon/directory
    
This will convert all Python files in:
    - Root directory
    - /resources/lib/
    - /schedulers/
    - /utilities/
    - Any other subdirectories

Creates backup before conversion.
"""

import os
import sys
import shutil
import argparse
from pathlib import Path
from datetime import datetime

# Import the converter class
sys.path.insert(0, os.path.dirname(__file__))
from kodi_py2_to_py3_converter import KodiPy2to3Converter


def find_all_python_files(directory):
    """Recursively find all Python files in directory"""
    python_files = []
    for root, dirs, files in os.walk(directory):
        # Skip __pycache__ and .git directories
        dirs[:] = [d for d in dirs if d not in ['__pycache__', '.git', '.svn', '.idea']]
        
        for file in files:
            if file.endswith('.py'):
                full_path = os.path.join(root, file)
                python_files.append(full_path)
    
    return sorted(python_files)


def create_backup(directory):
    """Create backup of entire addon directory"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_name = f"{directory}_backup_{timestamp}"
    
    print(f"\n🔄 Creating backup: {backup_name}")
    try:
        shutil.copytree(directory, backup_name, symlinks=True)
        print(f"✅ Backup created successfully!")
        return backup_name
    except Exception as e:
        print(f"❌ Error creating backup: {e}")
        return None


def convert_addon_directory(addon_path, create_backup_first=True):
    """Convert entire addon directory"""
    addon_path = Path(addon_path).resolve()
    
    if not addon_path.exists():
        print(f"❌ Error: Directory not found: {addon_path}")
        return False
    
    if not addon_path.is_dir():
        print(f"❌ Error: Not a directory: {addon_path}")
        return False
    
    print("="*70)
    print("KODI ADDON COMPLETE DIRECTORY CONVERSION")
    print("Python 2.7 → Python 3")
    print("="*70)
    print(f"\nAddon Directory: {addon_path}")
    
    # Create backup
    if create_backup_first:
        backup_path = create_backup(str(addon_path))
        if not backup_path:
            response = input("\n⚠️  Backup failed. Continue anyway? (yes/no): ")
            if response.lower() != 'yes':
                print("Aborted.")
                return False
    
    # Find all Python files
    print("\n🔍 Scanning for Python files...")
    py_files = find_all_python_files(addon_path)
    
    if not py_files:
        print("❌ No Python files found!")
        return False
    
    print(f"✅ Found {len(py_files)} Python files")
    
    # Show file structure
    print("\n📂 File structure:")
    for py_file in py_files:
        rel_path = Path(py_file).relative_to(addon_path)
        print(f"  • {rel_path}")
    
    # Confirm conversion
    print("\n" + "="*70)
    response = input(f"Convert all {len(py_files)} files? (yes/no): ")
    if response.lower() != 'yes':
        print("Aborted.")
        return False
    
    # Convert all files
    print("\n🔄 Converting files...")
    print("="*70)
    
    converter = KodiPy2to3Converter()
    converted_count = 0
    failed_files = []
    
    for i, py_file in enumerate(py_files, 1):
        rel_path = Path(py_file).relative_to(addon_path)
        print(f"\n[{i}/{len(py_files)}] Converting: {rel_path}")
        
        try:
            converted_content = converter.convert_file(py_file)
            
            if converted_content:
                # Write converted content back to file
                with open(py_file, 'w', encoding='utf-8') as f:
                    f.write(converted_content)
                print(f"  ✅ Converted successfully")
                converted_count += 1
            else:
                print(f"  ℹ️  No changes needed")
        
        except Exception as e:
            print(f"  ❌ Error: {e}")
            failed_files.append((rel_path, str(e)))
    
    # Handle addon.xml
    print("\n" + "="*70)
    print("🔄 Updating addon.xml...")
    addon_xml = addon_path / 'addon.xml'
    
    if addon_xml.exists():
        try:
            converted_xml = converter.convert_addon_xml(addon_xml)
            if converted_xml:
                with open(addon_xml, 'w', encoding='utf-8') as f:
                    f.write(converted_xml)
                print("  ✅ addon.xml updated (xbmc.python version → 3.0.0)")
            else:
                print("  ℹ️  addon.xml - no changes needed")
        except Exception as e:
            print(f"  ❌ Error updating addon.xml: {e}")
    else:
        print("  ⚠️  addon.xml not found in root directory")
    
    # Print summary
    print("\n" + "="*70)
    print("CONVERSION COMPLETE")
    print("="*70)
    print(f"\n📊 Statistics:")
    print(f"  • Total Python files: {len(py_files)}")
    print(f"  • Files converted: {converted_count}")
    print(f"  • Files unchanged: {len(py_files) - converted_count - len(failed_files)}")
    print(f"  • Failed conversions: {len(failed_files)}")
    
    if failed_files:
        print("\n❌ Failed files:")
        for file, error in failed_files:
            print(f"  • {file}: {error}")
    
    # Print conversion details
    if converter.conversions_made:
        print(f"\n✅ Conversions applied ({len(set(converter.conversions_made))}):")
        for conversion in sorted(set(converter.conversions_made)):
            print(f"  • {conversion}")
    
    if converter.warnings:
        print(f"\n⚠️  Warnings ({len(converter.warnings)}):")
        for warning in converter.warnings:
            print(f"  • {warning}")
    
    # Print critical next steps
    print("\n" + "="*70)
    print("🎯 CRITICAL NEXT STEPS")
    print("="*70)
    print("""
1. REVIEW all converted files manually
2. TEST on Kodi 21 (Python 3):
   - Install the converted addon
   - Enable debug logging (Settings → System → Logging)
   - Test ALL features thoroughly
   - Check ~/.kodi/temp/kodi.log for errors

3. TEST on Kodi 17.6 (Python 2.7) if supporting backward compatibility

4. Pay special attention to:
   - xbmc.log() calls (string encoding)
   - File operations (xbmcvfs)
   - Network requests (bytes vs strings)
   - JSON parsing
   - Database operations

5. Update version number in addon.xml

6. Create release notes

For detailed guidance, see MIGRATION_GUIDE.md
""")
    
    if create_backup_first and backup_path:
        print(f"💾 Backup saved at: {backup_path}")
        print("   (Restore if needed: just rename back to original)")
    
    print("\n" + "="*70)
    print("Good luck with testing! 🚀")
    print("="*70 + "\n")
    
    return True


def main():
    parser = argparse.ArgumentParser(
        description='Convert complete Kodi addon directory from Python 2.7 to Python 3',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Convert entire addon directory (with backup)
  python3 convert_complete_addon.py /path/to/addon
  
  # Convert without creating backup (not recommended!)
  python3 convert_complete_addon.py /path/to/addon --no-backup

The script will:
  1. Create a timestamped backup of your entire addon
  2. Find all Python files recursively
  3. Convert each file for Python 2/3 compatibility
  4. Update addon.xml xbmc.python version
  5. Provide detailed conversion report
"""
    )
    
    parser.add_argument(
        'addon_directory',
        help='Path to addon directory (e.g., script.paragontv)'
    )
    
    parser.add_argument(
        '--no-backup',
        action='store_true',
        help='Skip creating backup (NOT recommended)'
    )
    
    args = parser.parse_args()
    
    # Convert the addon
    success = convert_addon_directory(
        args.addon_directory,
        create_backup_first=not args.no_backup
    )
    
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
