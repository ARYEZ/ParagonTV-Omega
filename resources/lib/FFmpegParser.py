#   Copyright (C) 2025 Aryez
#
#
# This file is part of Paragon TV.
#
# Paragon TV is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Paragon TV is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Paragon TV.  If not, see <http://www.gnu.org/licenses/>.

import os
import subprocess
import json
import re
import xbmc
from Globals import ascii


class FFmpegParser:
    """
    Universal video parser using FFmpeg/FFprobe to get video duration.
    Works with MKV, MP4, AVI, and any other format FFmpeg supports.
    Bypasses the broken xbmcvfs.File() binary mode issue in Kodi 21 Python 3.
    
    Handles path conversion for Windows (NFS/SMB -> UNC paths)
    """
    
    def log(self, msg, level=xbmc.LOGDEBUG):
        try:
            xbmc.log("script.paragontv-FFmpegParser: " + ascii(msg), level)
        except:
            xbmc.log("script.paragontv-FFmpegParser: " + str(msg), level)

    def _convert_path_for_ffmpeg(self, filename):
        """
        Convert Kodi virtual paths to paths that ffmpeg can understand.
        
        On Windows:
        - nfs://10.0.0.39/mnt/user/TELEVISION/file.mkv -> //10.0.0.39/mnt/user/TELEVISION/file.mkv
        - smb://10.0.0.39/share/file.mkv -> //10.0.0.39/share/file.mkv
        
        On Linux/Unix:
        - Keep paths as-is since ffmpeg handles network paths directly
        
        Args:
            filename: Kodi path (may be NFS, SMB, or local)
            
        Returns:
            Path that ffmpeg can access
        """
        original = filename
        
        # Check if Windows
        is_windows = os.name == 'nt' or os.sep == '\\'
        
        if is_windows:
            # Convert nfs:// to UNC path using forward slashes (ffmpeg on Windows accepts these)
            if filename.startswith('nfs://'):
                # nfs://10.0.0.39/mnt/user/TELEVISION/file.mkv
                # -> //10.0.0.39/mnt/user/TELEVISION/file.mkv
                filename = filename.replace('nfs://', '//')
                self.log("Converted NFS to UNC: " + original + " -> " + filename)
                
            # Convert smb:// to UNC path
            elif filename.startswith('smb://'):
                # smb://10.0.0.39/share/file.mkv
                # -> //10.0.0.39/share/file.mkv
                filename = filename.replace('smb://', '//')
                self.log("Converted SMB to UNC: " + original + " -> " + filename)
        
        return filename

    def determineLength(self, filename):
        """
        Get video duration using FFprobe (comes with FFmpeg).
        
        Args:
            filename: Full path to video file (supports NFS, SMB, local paths)
            
        Returns:
            Duration in seconds (float), or 0 if unable to determine
        """
        self.log("determineLength " + filename)
        
        # Convert path for ffmpeg
        converted_path = self._convert_path_for_ffmpeg(filename)
        
        try:
            # Try ffprobe first (more reliable for just getting duration)
            duration = self._probe_with_ffprobe(converted_path)
            
            if duration > 0:
                self.log("Duration from ffprobe: " + str(duration))
                return duration
            
            # Fallback to ffmpeg if ffprobe not available or failed
            duration = self._probe_with_ffmpeg(converted_path)
            
            if duration > 0:
                self.log("Duration from ffmpeg: " + str(duration))
                return duration
                
        except Exception as e:
            self.log("Error determining length: " + str(e), xbmc.LOGERROR)
        
        self.log("Duration is 0")
        return 0

    def _probe_with_ffprobe(self, filename):
        """Use ffprobe to get duration (preferred method)"""
        try:
            # ffprobe command to get duration in JSON format
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                filename
            ]
            
            self.log("Running ffprobe...")
            
            # Run ffprobe
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30,
                text=True
            )
            
            if result.returncode != 0:
                self.log("ffprobe failed with code " + str(result.returncode))
                if result.stderr:
                    # Log first line of error only (don't spam log)
                    error_lines = result.stderr.split('\n')
                    for line in error_lines[:3]:  # First 3 lines
                        if line.strip():
                            self.log("ffprobe error: " + line.strip())
                return 0
            
            # Parse JSON output
            data = json.loads(result.stdout)
            
            if 'format' in data and 'duration' in data['format']:
                duration = float(data['format']['duration'])
                return duration
                
        except FileNotFoundError:
            self.log("ffprobe not found, will try ffmpeg")
        except subprocess.TimeoutExpired:
            self.log("ffprobe timeout", xbmc.LOGWARNING)
        except json.JSONDecodeError as e:
            self.log("Failed to parse ffprobe JSON output: " + str(e), xbmc.LOGWARNING)
        except Exception as e:
            self.log("ffprobe error: " + str(e))
        
        return 0

    def _probe_with_ffmpeg(self, filename):
        """Use ffmpeg to get duration (fallback method)"""
        try:
            # ffmpeg command - just try to read the file, it will output duration
            cmd = [
                'ffmpeg',
                '-i', filename,
                '-f', 'null',
                '-'
            ]
            
            self.log("Running ffmpeg...")
            
            # Run ffmpeg (it outputs to stderr)
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30,
                text=True
            )
            
            # Parse stderr for duration line
            # Format: "Duration: 00:59:58.40, start: 0.000000, bitrate: 4033 kb/s"
            for line in result.stderr.split('\n'):
                if 'Duration:' in line:
                    # Extract duration string
                    duration_str = line.split('Duration:')[1].split(',')[0].strip()
                    
                    # Check for N/A
                    if duration_str == 'N/A':
                        self.log("ffmpeg reported duration N/A")
                        return 0
                    
                    # Parse HH:MM:SS.ms format
                    parts = duration_str.split(':')
                    if len(parts) == 3:
                        try:
                            hours = float(parts[0])
                            minutes = float(parts[1])
                            seconds = float(parts[2])
                            
                            total_seconds = hours * 3600 + minutes * 60 + seconds
                            return total_seconds
                        except ValueError:
                            self.log("Failed to parse duration: " + duration_str)
                            return 0
                        
        except FileNotFoundError:
            self.log("ffmpeg not found", xbmc.LOGERROR)
        except subprocess.TimeoutExpired:
            self.log("ffmpeg timeout", xbmc.LOGWARNING)
        except Exception as e:
            self.log("ffmpeg error: " + str(e))
        
        return 0

    def _format_duration(self, seconds):
        """Format seconds as HH:MM:SS for logging"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return "{:02d}:{:02d}:{:02d}".format(hours, minutes, secs)