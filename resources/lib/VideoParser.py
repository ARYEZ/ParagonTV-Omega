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

import xbmc
from FileAccess import FileAccess
from FFmpegParser import FFmpegParser
from Globals import ascii


class VideoParser:
    def __init__(self):
        pass

    def log(self, msg, level=xbmc.LOGDEBUG):
        try:
            xbmc.log("script.paragontv-VideoParser: " + ascii(msg), level)
        except:
            xbmc.log("script.paragontv-VideoParser: " + str(msg), level)

    def getVideoLength(self, filename):
        """
        Get video duration using FFmpegParser.
        
        This replaces the old MKVParser/MP4Parser methods which were broken
        in Kodi 21 Python 3 due to xbmcvfs.File() binary mode issues.
        
        FFmpegParser uses ffprobe/ffmpeg subprocess calls to get accurate
        durations for all video formats without relying on xbmcvfs.
        
        Args:
            filename: Full path to video file (NFS, SMB, or local)
            
        Returns:
            Duration in seconds (float), or 0 if unable to determine
        """
        self.log("getVideoLength " + filename)
        
        # Check if file exists
        if FileAccess.exists(filename) == False:
            self.log("Unable to find the file")
            return 0
        
        # Use FFmpegParser for all video formats
        # Works with: MKV, MP4, AVI, WMV, FLV, MOV, etc.
        parser = FFmpegParser()
        duration = parser.determineLength(filename)
        
        return duration