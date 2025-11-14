#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals

import sys
# Python 2/3 compatibility
if sys.version_info[0] >= 3:
    unicode = str
    basestring = str


# Set default encoding to UTF-8
reload(sys)
sys.setdefaultencoding("utf-8")

"""
NFO Renamer Television

This script reads TV show NFO files and renames associated video files to the extended format:
SSxEE - Episode Title - Show Title - Genre - Resolution - Audio Channels - Audio Codec - Holiday.ext

It preserves the original NFO file content but renames both the NFO and video files.
Genre and show title information are obtained from tvshow.nfo if not available in episode NFO.
Holiday detection (Christmas/Thanksgiving/Halloween/None) is based on plot text analysis.

IMPROVED: 
- Now skips files that are already in the correct format
- Sanitizes filenames to remove invalid Windows characters
- Handles colons and other special characters in filenames
- Properly handles Unicode characters in filenames and content
- Reads directory from addon settings (Kodi-style)
- Uses xbmcvfs for NFS/SMB path support
- Automatic XML error fixing for malformed NFO files
"""

import logging
import os
import re
import shutil
import xml.etree.ElementTree as ET

import xbmc
import xbmcaddon
import xbmcvfs

# Get addon reference
ADDON_ID = 'script.paragontv'
ADDON = xbmcaddon.Addon(ADDON_ID)

# Configure logging - to Kodi log
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

def log(msg, level=xbmc.LOGINFO):
    """Log to Kodi log"""
    xbmc.log('[NFO Renamer Television] ' + str(msg), level)

def notify(msg, title='NFO Renamer'):
    """Show Kodi notification with Paragon TV icon"""
    icon = ADDON.getAddonInfo('icon')
    # Remove commas from message to prevent Kodi parsing issues
    msg_clean = msg.replace(',', ' -')
    xbmc.executebuiltin('Notification({}, {}, 5000, {})'.format(title, msg_clean, icon))

# Video file extensions to process
VIDEO_EXTENSIONS = [".mkv", ".mp4", ".avi", ".m4v", ".ts", ".mov"]
# Resolution mapping
RESOLUTION_MAP = {
    "2160p": "2160",
    "4k": "2160",
    "4K": "2160",
    "1080p": "1080",
    "1080P": "1080",
    "720p": "720",
    "720P": "720",
    "480p": "480",
    "480P": "480",
    "SD": "480",
}

# Common audio codec mappings (abbreviations to standardized forms)
AUDIO_CODEC_MAP = {
    "ac3": "AC3",
    "eac3": "EAC3",
    "dts": "DTS",
    "dtshd": "DTS-HD",
    "truehd": "TrueHD",
    "aac": "AAC",
    "mp3": "MP3",
    "flac": "FLAC",
    "pcm": "PCM",
    "dca": "DTS",  # DCA is often used for DTS
    "opus": "OPUS",
}

# Holiday keywords to search for in plot text
HOLIDAY_KEYWORDS = {
    "Christmas": ["christmas", "xmas", "santa", "december 25", "noel", "yule"],
    "Thanksgiving": ["thanksgiving", "turkey day", "pilgrim"],
    "Halloween": [
        "halloween",
        "trick or treat",
        "trick-or-treat",
        "spooky",
        "october 31",
        "all hallows",
    ],
}

# Invalid characters for Windows filenames
INVALID_FILENAME_CHARS = ["<", ">", ":", '"', "/", "\\", "|", "?", "*"]

# Cache for tvshow.nfo metadata to avoid re-parsing the same file multiple times
tvshow_metadata_cache = {}

# Pattern to detect if a file is already in the extended format
# Format: SSxEE - Episode Title - Show Title - Genre - Resolution - Audio Channels - Audio Codec - Holiday.ext
# Accepts both 1x01 and 01x01 formats
EXTENDED_FORMAT_PATTERN = re.compile(
    r"^\d{1,2}x\d{1,2} - .+ - .+ - .+ - \d+ - \d+ - [A-Za-z0-9-]+ - [A-Za-z]+"
)


# Function to sanitize filenames for Windows compatibility
def sanitize_filename(filename):
    """
    Remove or replace characters that are invalid in Windows filenames
    Properly handles Unicode characters
    """
    # Ensure we're working with Unicode
    if not isinstance(filename, unicode):
        try:
            filename = filename
        except UnicodeDecodeError:
            # If UTF-8 decoding fails, try with error replacement
            filename = filename.decode("utf-8", "replace")

    # Replace colons with a safe alternative
    sanitized = filename.replace(":", ".")

    # Replace other invalid characters
    for char in INVALID_FILENAME_CHARS:
        if char in sanitized:
            sanitized = sanitized.replace(char, "_")

    # Replace multiple periods with a single period
    sanitized = re.sub(r"\.+", ".", sanitized)

    # Check if the filename is valid after sanitization
    if sanitized != filename:
        log("Sanitized filename: '{}' -> '{}'".format(
            filename.encode("utf-8", "replace"),
            sanitized.encode("utf-8", "replace")
        ))

    return sanitized


def remove_problematic_chars(text):
    """
    Remove emojis and other problematic Unicode characters that cause MySQL encoding issues
    This includes:
    - Emojis (U+1F300 to U+1F9FF range and others)
    - Various symbol ranges that require utf8mb4
    - Other 4-byte UTF-8 characters
    
    Returns cleaned text that's safe for utf8 (3-byte) MySQL databases
    """
    if not text:
        return text
    
    # Ensure we're working with Unicode
    if not isinstance(text, unicode):
        try:
            text = text
        except UnicodeDecodeError:
            text = text.decode("utf-8", "replace")
    
    # Remove 4-byte UTF-8 characters (emojis and other special symbols)
    # This regex matches characters outside the Basic Multilingual Plane (BMP)
    import re
    # Remove emojis and other 4-byte UTF-8 chars
    # Match any character with code point > U+FFFF (requires surrogate pairs in UTF-16, 4 bytes in UTF-8)
    cleaned = re.sub(r'[^\u0000-\uFFFF]', '', text)
    
    # Also explicitly remove common emoji ranges within BMP
    emoji_pattern = re.compile("["
        u"\U0001F600-\U0001F64F"  # emoticons
        u"\U0001F300-\U0001F5FF"  # symbols & pictographs
        u"\U0001F680-\U0001F6FF"  # transport & map symbols
        u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
        u"\U00002702-\U000027B0"  # dingbats
        u"\U000024C2-\U0001F251"
        u"\U0001F900-\U0001F9FF"  # supplemental symbols
        u"\U00002600-\U000026FF"  # misc symbols
        u"\U00002700-\U000027BF"  # dingbats
        "]+", flags=re.UNICODE)
    
    cleaned = emoji_pattern.sub('', cleaned)
    
    # Clean up any resulting extra whitespace
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    
    if cleaned != text:
        log("Removed problematic characters from text (length: {} -> {})".format(
            len(text), len(cleaned)
        ))
    
    return cleaned


# Function to check if a file is already in the extended format
def is_already_extended_format(filename):
    """
    Check if the filename is already in the extended format
    Returns True if it matches the pattern AND has no None values in show/genre, False otherwise
    """
    # Ensure we're working with Unicode
    if not isinstance(filename, unicode):
        try:
            filename = filename
        except UnicodeDecodeError:
            # If UTF-8 decoding fails, try with error replacement
            filename = filename.decode("utf-8", "replace")

    # Strip extension
    base_name = os.path.splitext(filename)[0]

    # Check if we have at least 7 hyphens (for 8 parts)
    if base_name.count(" - ") < 7:
        return False

    # Check if it matches the pattern
    if not EXTENDED_FORMAT_PATTERN.match(base_name):
        return False

    # More detailed analysis: check format parts
    parts = base_name.split(" - ")

    # Check if first part matches SSxEE format (1-2 digits for each)
    if not re.match(r"^\d{1,2}x\d{1,2}$", parts[0]):
        return False

    # Check if we have the correct number of parts
    if len(parts) < 8:
        return False

    # If resolution part exists and is numeric
    if not parts[4].isdigit():
        return False

    # If audio channels part exists and is numeric
    if not parts[5].isdigit():
        return False

    # If holiday part exists and is valid
    if parts[7] not in ["Christmas", "Thanksgiving", "Halloween", "None"]:
        return False

    # NEW: Check if show title (part 2) or genre (part 3) is "None" or "Unknown"
    # If either is None/Unknown, the file needs to be re-renamed
    show_title = parts[2] if len(parts) > 2 else ""
    genre = parts[3] if len(parts) > 3 else ""
    
    if show_title in ["None", "Unknown"] or genre in ["None", "Unknown"]:
        return False  # Needs to be renamed with correct metadata

    # If we got here, it's already in the extended format with good metadata
    return True


def detect_holiday(plot_text):
    """
    Detect holiday references in the plot text
    Returns 'Christmas', 'Thanksgiving', 'Halloween', or 'None' based on keywords found
    """
    if not plot_text:
        return "None"

    # Ensure we're working with Unicode
    if not isinstance(plot_text, unicode):
        try:
            plot_text = plot_text
        except UnicodeDecodeError:
            # If UTF-8 decoding fails, try with error replacement
            plot_text = plot_text.decode("utf-8", "replace")

    # Convert to lowercase for case-insensitive matching
    plot_lower = plot_text.lower()

    # Check for each holiday's keywords
    for holiday, keywords in HOLIDAY_KEYWORDS.items():
        for keyword in keywords:
            if keyword in plot_lower:
                log("Detected {} episode based on keyword '{}'".format(holiday, keyword))
                return holiday

    return "None"


def parse_nfo_file(nfo_path):
    """
    Parse NFO file and extract metadata including holiday detection
    Returns a dictionary with metadata or None if parsing fails
    """
    try:
        # Use xbmcvfs.File for NFS path support
        nfo_file = xbmcvfs.File(nfo_path)
        content = nfo_file.read()
        nfo_file.close()

        # Ensure content is UTF-8
        if not isinstance(content, unicode):
            try:
                content = content
            except UnicodeDecodeError:
                content = content.decode("utf-8", "replace")

        # Parse XML
        try:
            root = ET.fromstring(content.encode("utf-8"))
        except ET.ParseError as parse_error:
            # Try to fix common XML issues (unescaped ampersands, etc.)
            log("Initial XML parse failed, attempting to fix common issues...", xbmc.LOGWARNING)
            
            # Fix unescaped ampersands (but not already-escaped ones like &amp;)
            import re
            # Replace & that's not part of an entity (not followed by amp;, lt;, gt;, quot;, apos;, or #)
            content = re.sub(r'&(?!(amp|lt|gt|quot|apos|#\d+|#x[0-9a-fA-F]+);)', '&amp;', content)
            
            try:
                root = ET.fromstring(content.encode("utf-8"))
                log("Successfully parsed after fixing XML issues", xbmc.LOGINFO)
            except ET.ParseError:
                # Still failed, give up
                raise parse_error

        # Extract metadata
        metadata = {
            "title": None,
            "season": None,
            "episode": None,
            "genre": None,
            "showtitle": None,
            "resolution": None,
            "audio_channels": None,
            "audio_codec": None,
            "plot": None,
            "holiday": "None",  # Default to None
        }

        # Extract basic information
        title_elem = root.find("title")
        if title_elem is not None and title_elem.text:
            metadata["title"] = remove_problematic_chars(title_elem.text.strip())

        season_elem = root.find("season")
        if season_elem is not None and season_elem.text:
            try:
                metadata["season"] = int(season_elem.text.strip())
            except ValueError:
                log("Could not parse season: {}".format(season_elem.text), xbmc.LOGWARNING)

        episode_elem = root.find("episode")
        if episode_elem is not None and episode_elem.text:
            try:
                metadata["episode"] = int(episode_elem.text.strip())
            except ValueError:
                log("Could not parse episode: {}".format(episode_elem.text), xbmc.LOGWARNING)

        # Extract genre
        genre_elem = root.find("genre")
        if genre_elem is not None and genre_elem.text:
            metadata["genre"] = remove_problematic_chars(genre_elem.text.strip())

        # Extract show title
        showtitle_elem = root.find("showtitle")
        if showtitle_elem is not None and showtitle_elem.text:
            metadata["showtitle"] = remove_problematic_chars(showtitle_elem.text.strip())

        # Extract plot for holiday detection
        plot_elem = root.find("plot")
        if plot_elem is not None and plot_elem.text:
            metadata["plot"] = remove_problematic_chars(plot_elem.text.strip())
            # Detect holiday from plot
            metadata["holiday"] = detect_holiday(metadata["plot"])

        # Try to extract technical info from fileinfo tag if available
        fileinfo = root.find("fileinfo")
        if fileinfo is not None:
            streamdetails = fileinfo.find("streamdetails")
            if streamdetails is not None:
                # Get video resolution
                video = streamdetails.find("video")
                if video is not None:
                    width_elem = video.find("width")
                    height_elem = video.find("height")
                    if height_elem is not None and height_elem.text:
                        try:
                            height = int(height_elem.text.strip())
                            # Map height to resolution
                            if height >= 2160:
                                metadata["resolution"] = "2160"
                            elif height >= 1080:
                                metadata["resolution"] = "1080"
                            elif height >= 720:
                                metadata["resolution"] = "720"
                            else:
                                metadata["resolution"] = "480"
                        except ValueError:
                            pass

                # Get audio information
                audio = streamdetails.find("audio")
                if audio is not None:
                    # Get audio channels
                    channels_elem = audio.find("channels")
                    if channels_elem is not None and channels_elem.text:
                        metadata["audio_channels"] = channels_elem.text.strip()

                    # Get audio codec
                    codec_elem = audio.find("codec")
                    if codec_elem is not None and codec_elem.text:
                        codec = codec_elem.text.strip().lower()
                        # Standardize codec name
                        metadata["audio_codec"] = AUDIO_CODEC_MAP.get(
                            codec, codec.upper()
                        )

        return metadata

    except ET.ParseError as e:
        log("XML parse error in {}: {}".format(nfo_path, e), xbmc.LOGERROR)
        return None
    except Exception as e:
        log("Error parsing NFO file {}: {}".format(nfo_path, e), xbmc.LOGERROR)
        return None


def get_tvshow_metadata(episode_nfo_path):
    """
    Get metadata from tvshow.nfo in the parent directory
    Returns a dictionary with genre and showtitle, or empty values if not found
    Uses caching to avoid re-parsing the same tvshow.nfo file multiple times
    """
    # Get the directory containing the episode NFO
    episode_dir = os.path.dirname(episode_nfo_path)

    # Check if metadata is already cached
    if episode_dir in tvshow_metadata_cache:
        return tvshow_metadata_cache[episode_dir]

    # Initialize default metadata
    metadata = {"genre": None, "showtitle": None}

    # Look for tvshow.nfo in multiple locations:
    # 1. Same directory as episode (for flat structure)
    # 2. Parent directory (for Season X folder structure)
    tvshow_paths = [
        os.path.join(episode_dir, "tvshow.nfo"),  # Same directory
        os.path.join(os.path.dirname(episode_dir), "tvshow.nfo"),  # Parent directory
    ]

    tvshow_nfo_path = None
    for path in tvshow_paths:
        if xbmcvfs.exists(path):  # Use xbmcvfs.exists() for NFS support!
            tvshow_nfo_path = path
            log("Found tvshow.nfo at: {}".format(path))
            break

    if not tvshow_nfo_path:
        log("No tvshow.nfo found for: {}".format(episode_nfo_path), xbmc.LOGWARNING)
        # Cache the empty result
        tvshow_metadata_cache[episode_dir] = metadata
        return metadata

    try:
        # Use xbmcvfs.File for NFS path support
        nfo_file = xbmcvfs.File(tvshow_nfo_path)
        content = nfo_file.read()
        nfo_file.close()

        # Ensure content is UTF-8
        if not isinstance(content, unicode):
            try:
                content = content
            except UnicodeDecodeError:
                content = content.decode("utf-8", "replace")

        # Parse XML
        root = ET.fromstring(content.encode("utf-8"))

        # Extract genre
        genre_elem = root.find("genre")
        if genre_elem is not None and genre_elem.text:
            metadata["genre"] = genre_elem.text.strip()

        # Extract show title
        title_elem = root.find("title")
        if title_elem is not None and title_elem.text:
            metadata["showtitle"] = title_elem.text.strip()

        # Cache the result
        tvshow_metadata_cache[episode_dir] = metadata
        return metadata

    except Exception as e:
        log("Could not parse tvshow.nfo at {}: {}".format(tvshow_nfo_path, e), xbmc.LOGWARNING)
        # Cache the empty result
        tvshow_metadata_cache[episode_dir] = metadata
        return metadata


def get_resolution_from_filename(filename):
    """
    Extract resolution from filename
    Returns resolution string or None if not found
    """
    filename_lower = filename.lower()
    for pattern, resolution in RESOLUTION_MAP.items():
        if pattern.lower() in filename_lower:
            return resolution
    return None


def create_extended_filename(metadata, original_extension):
    """
    Create the extended filename format:
    SSxEE - Episode Title - Show Title - Genre - Resolution - Audio Channels - Audio Codec - Holiday.ext
    """
    # Build season/episode string with zero-padding for both season and episode
    season = metadata.get("season", 0)
    episode = metadata.get("episode", 0)
    season_episode = "{:02d}x{:02d}".format(season, episode)  # Changed to pad both

    # Get episode title (required)
    title = metadata.get("title", "Unknown")

    # Get show title (required)
    showtitle = metadata.get("showtitle", "Unknown")

    # Get genre (required)
    genre = metadata.get("genre", "Unknown")

    # Get resolution (required)
    resolution = metadata.get("resolution", "Unknown")

    # Get audio channels (required)
    audio_channels = metadata.get("audio_channels", "Unknown")

    # Get audio codec (required)
    audio_codec = metadata.get("audio_codec", "Unknown")

    # Get holiday (required, defaults to "None")
    holiday = metadata.get("holiday", "None")

    # Construct filename
    parts = [
        season_episode,
        title,
        showtitle,
        genre,
        resolution,
        audio_channels,
        audio_codec,
        holiday,
    ]

    # Join with " - " separator
    filename = " - ".join(str(part) for part in parts)

    # Sanitize the filename
    filename = sanitize_filename(filename)

    return filename


def rename_files(directory, dry_run=False, recursive=False):
    """
    Process directory and rename files based on NFO metadata
    Returns statistics dictionary
    """
    stats = {
        "processed": 0,
        "renamed": 0,
        "skipped": 0,
        "errors": 0,
        "already_extended": 0,
        "genre_from_tvshow": 0,
        "showtitle_from_tvshow": 0,
        "christmas_episodes": 0,
        "thanksgiving_episodes": 0,
        "halloween_episodes": 0,
    }

    log("Processing directory: {}".format(directory))

    # Walk through directory (recursive or not)
    if recursive:
        walk_directory_recursive(directory, stats, dry_run)
    else:
        # Use xbmcvfs.listdir for NFS path support
        dirs, files = xbmcvfs.listdir(directory)
        process_directory(directory, files, stats, dry_run)

    return stats


def walk_directory_recursive(directory, stats, dry_run):
    """Recursively walk through directories using xbmcvfs"""
    try:
        # Get list of subdirectories and files
        dirs, files = xbmcvfs.listdir(directory)
        
        # Process files in current directory
        process_directory(directory, files, stats, dry_run)
        
        # Recursively process subdirectories
        for subdir in dirs:
            subdir_path = os.path.join(directory, subdir)
            walk_directory_recursive(subdir_path, stats, dry_run)
    except Exception as e:
        log("Error accessing directory {}: {}".format(directory, e), xbmc.LOGERROR)


def process_directory(directory, files, stats, dry_run):
    """Process all NFO files in a directory"""
    for filename in files:
        if not filename.endswith(".nfo"):
            continue

        # Skip tvshow.nfo
        if filename.lower() == "tvshow.nfo":
            continue

        base_name, _ = os.path.splitext(filename)

        # Look for corresponding video file
        video_file = None
        video_ext = None
        for ext in VIDEO_EXTENSIONS:
            potential_video = base_name + ext
            if potential_video in files:
                video_file = potential_video
                video_ext = ext
                break

        if not video_file:
            log("No video file found for NFO: {}".format(filename), xbmc.LOGWARNING)
            stats["skipped"] += 1
            continue

        stats["processed"] += 1

        # Check if already in extended format
        if is_already_extended_format(video_file):
            log("File already in extended format: {}".format(video_file))
            stats["already_extended"] += 1
            stats["skipped"] += 1
            continue

        # Parse NFO file
        full_nfo_path = os.path.join(directory, filename)
        metadata = parse_nfo_file(full_nfo_path)
        if not metadata:
            log("Failed to parse NFO: {}".format(filename), xbmc.LOGERROR)
            stats["errors"] += 1
            continue

        # If we're missing critical metadata, try to extract from filename
        if metadata["season"] is None or metadata["episode"] is None:
            # Try to extract season and episode from filename
            season_ep_match = re.search(r"[sS](\d+)[eE](\d+)", base_name)
            if season_ep_match:
                metadata["season"] = int(season_ep_match.group(1))
                metadata["episode"] = int(season_ep_match.group(2))
            else:
                # Try NxNN format
                season_ep_match = re.search(r"(\d+)x(\d+)", base_name)
                if season_ep_match:
                    metadata["season"] = int(season_ep_match.group(1))
                    metadata["episode"] = int(season_ep_match.group(2))

        # Get missing metadata from tvshow.nfo
        need_tvshow_metadata = False
        if not metadata["genre"] or not metadata["showtitle"]:
            need_tvshow_metadata = True

        if need_tvshow_metadata:
            tvshow_metadata = get_tvshow_metadata(full_nfo_path)

            # If genre is missing, get it from tvshow.nfo
            if not metadata["genre"] and tvshow_metadata["genre"]:
                metadata["genre"] = tvshow_metadata["genre"]
                stats["genre_from_tvshow"] += 1
                log("Using genre from tvshow.nfo: {}".format(tvshow_metadata["genre"]))

            # If show title is missing, get it from tvshow.nfo
            if not metadata["showtitle"] and tvshow_metadata["showtitle"]:
                metadata["showtitle"] = tvshow_metadata["showtitle"]
                stats["showtitle_from_tvshow"] += 1
                log("Using show title from tvshow.nfo: {}".format(tvshow_metadata["showtitle"]))

        # Update holiday statistics
        if metadata["holiday"] == "Christmas":
            stats["christmas_episodes"] += 1
        elif metadata["holiday"] == "Thanksgiving":
            stats["thanksgiving_episodes"] += 1
        elif metadata["holiday"] == "Halloween":
            stats["halloween_episodes"] += 1

        # If resolution not in NFO, try to get from filename
        if not metadata["resolution"]:
            metadata["resolution"] = get_resolution_from_filename(base_name)

        # Try to extract audio information from filename if not in NFO
        if not metadata["audio_channels"] or metadata["audio_channels"] == "None":
            # Look for patterns like "5.1" or "7.1" for channels
            channels_match = re.search(
                r"(\d+\.\d+)ch|(\d+)ch|(\d+\.\d+)|(\d+)channels", base_name.lower()
            )
            if channels_match:
                # Use the first non-None group
                for group in channels_match.groups():
                    if group:
                        metadata["audio_channels"] = group
                        break

        if not metadata["audio_codec"] or metadata["audio_codec"] == "None":
            # Look for audio codec indicators
            for codec, standardized in AUDIO_CODEC_MAP.items():
                if codec.lower() in base_name.lower():
                    metadata["audio_codec"] = standardized
                    break

        # Create new filenames
        new_base_name = create_extended_filename(metadata, "")
        new_video_name = new_base_name + video_ext
        new_nfo_name = new_base_name + ".nfo"

        # Check if rename is actually needed (names might already match)
        if new_video_name == video_file and new_nfo_name == filename:
            log("Files already have correct naming: {}".format(filename))
            stats["skipped"] += 1
            continue

        # Log the rename operation
        log("Renaming:\n  {} -> {}\n  {} -> {}".format(
            filename, new_nfo_name, video_file, new_video_name
        ))

        # Rename files
        if not dry_run:
            try:
                # Rename video file
                video_src = os.path.join(directory, video_file)
                video_dst = os.path.join(directory, new_video_name)
                xbmcvfs.rename(video_src, video_dst)

                # Rename NFO file
                nfo_src = os.path.join(directory, filename)
                nfo_dst = os.path.join(directory, new_nfo_name)
                xbmcvfs.rename(nfo_src, nfo_dst)

                stats["renamed"] += 1
            except Exception as e:
                log("Error renaming files: {}".format(e), xbmc.LOGERROR)
                stats["errors"] += 1


def run_renamer(directory, dry_run=False, recursive=False):
    """Run the renamer with specified parameters"""
    # Send startup notification
    notify('Starting TV show renaming...', 'NFO Renamer')
    
    log("=" * 70)
    log("NFO RENAMER - TELEVISION")
    log("=" * 70)
    log("Processing directory: {}".format(directory))
    log("Recursive mode: {}".format("Yes" if recursive else "No"))
    log("Dry run mode: {}".format("Yes" if dry_run else "No"))

    if dry_run:
        log("*** DRY RUN MODE - NO FILES WILL BE MODIFIED ***")

    try:
        stats = rename_files(directory, dry_run, recursive)
        if stats:
            log("=" * 70)
            log("OPERATION COMPLETED")
            log("=" * 70)
            log("Files processed: {}".format(stats["processed"]))
            log("Files renamed: {}".format(stats["renamed"]))
            log("Files skipped: {}".format(stats["skipped"]))
            log("Files already in extended format: {}".format(stats["already_extended"]))
            log("Errors encountered: {}".format(stats["errors"]))
            log("Genre from tvshow.nfo: {}".format(stats["genre_from_tvshow"]))
            log("Show title from tvshow.nfo: {}".format(stats["showtitle_from_tvshow"]))
            log("Holiday episodes found:")
            log("  Christmas: {}".format(stats["christmas_episodes"]))
            log("  Thanksgiving: {}".format(stats["thanksgiving_episodes"]))
            log("  Halloween: {}".format(stats["halloween_episodes"]))
            log("=" * 70)
            
            # Send completion notification
            notify('TV renaming complete: {} renamed, {} skipped'.format(
                stats["renamed"], stats["skipped"]
            ), 'NFO Renamer')
            
            return 0
    except Exception as e:
        log("An error occurred: {}".format(e), xbmc.LOGERROR)
        import traceback
        log(traceback.format_exc(), xbmc.LOGERROR)
        
        # Send error notification
        notify('TV renaming failed - check log', 'NFO Renamer Error')
        
        return 1


def main():
    """Main function - reads directory from addon settings"""
    log("Script started")
    
    # Try to get directory from sys.argv first (if passed)
    directory = None
    dry_run = False
    recursive = True  # Television always need recursive since they're organized in subdirectories
    
    if len(sys.argv) > 1:
        directory = sys.argv[1]
        log("Directory from sys.argv: {}".format(directory))
        
        # Check for flags
        for arg in sys.argv[2:]:
            if arg == '--recursive' or arg == '-r':
                recursive = True
            elif arg == '--dry-run' or arg == '-d':
                dry_run = True
            elif arg == '--no-recursive':
                recursive = False
    
    # If no directory from args, try addon settings
    if not directory:
        try:
            directory = ADDON.getSetting('NFOTelevisionPath')
            log("Directory from settings: {}".format(directory))
        except:
            pass
    
    if not directory:
        log("No directory configured - please set NFOTelevisionPath in addon settings", xbmc.LOGERROR)
        return 1
    
    return run_renamer(directory, dry_run, recursive)


if __name__ == "__main__":
    try:
        result = main()
        sys.exit(result)
    except Exception as e:
        log("Fatal error: {}".format(e), xbmc.LOGERROR)
        import traceback
        log(traceback.format_exc(), xbmc.LOGERROR)
        sys.exit(1)