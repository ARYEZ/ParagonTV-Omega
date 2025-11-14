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
import struct

import xbmc
from FileAccess import FileAccess
from Globals import ascii


class MP4DataBlock:
    def __init__(self):
        self.size = -1
        self.boxtype = b""  # Store as bytes
        self.data = b""


class MP4MovieHeader:
    def __init__(self):
        self.version = 0
        self.flags = 0
        self.created = 0
        self.modified = 0
        self.scale = 0
        self.duration = 0


class MP4Parser:
    def __init__(self):
        self.MovieHeader = MP4MovieHeader()

    def log(self, msg, level=xbmc.LOGDEBUG):
        xbmc.log("MP4Parser: " + ascii(msg), level)

    def _ensure_bytes(self, data):
        """Convert string to bytes if needed (Python 3 compatibility)"""
        if data is None:
            return b''
        if isinstance(data, bytes):
            return data
        if isinstance(data, str):
            return data.encode('latin1')
        return data

    def determineLength(self, filename):
        self.log("determineLength " + filename)

        try:
            self.File = FileAccess.open(filename, "rb", None)
        except:
            self.log("Unable to open the file")
            return

        dur = self.readHeader()
        self.File.close()
        self.log("Duration: " + str(dur))
        return dur

    def readHeader(self):
        data = self.readBlock()

        if data.boxtype != b"ftyp":
            self.log("No file block, got: %s" % data.boxtype)
            return 0

        # Skip past the file header
        try:
            self.File.seek(data.size, 1)
        except:
            self.log("Error while seeking")
            return 0

        data = self.readBlock()

        while data.boxtype != b"moov" and data.size > 0:
            try:
                self.File.seek(data.size, 1)
            except:
                self.log("Error while seeking")
                return 0

            data = self.readBlock()

        data = self.readBlock()

        while data.boxtype != b"mvhd" and data.size > 0:
            try:
                self.File.seek(data.size, 1)
            except:
                self.log("Error while seeking")
                return 0

            data = self.readBlock()

        self.readMovieHeader()

        if self.MovieHeader.scale > 0 and self.MovieHeader.duration > 0:
            return int(self.MovieHeader.duration / self.MovieHeader.scale)

        return 0

    def readMovieHeader(self):
        try:
            data = self.File.read(1)
            data = self._ensure_bytes(data)  # FIXED
            if not data or len(data) == 0:
                self.MovieHeader.duration = 0
                return
            
            self.MovieHeader.version = struct.unpack(">b", data)[0]
            
            flags_data = self.File.read(3)
            flags_data = self._ensure_bytes(flags_data)  # FIXED
            if not flags_data or len(flags_data) < 3:
                self.MovieHeader.duration = 0
                return

            if self.MovieHeader.version == 1:
                header_data = self.File.read(36)
                header_data = self._ensure_bytes(header_data)  # FIXED
                if not header_data or len(header_data) < 36:
                    self.MovieHeader.duration = 0
                    return
                data = struct.unpack(">QQIQQ", header_data)
            else:
                header_data = self.File.read(20)
                header_data = self._ensure_bytes(header_data)  # FIXED
                if not header_data or len(header_data) < 20:
                    self.MovieHeader.duration = 0
                    return
                data = struct.unpack(">IIIII", header_data)

            self.MovieHeader.created = data[0]
            self.MovieHeader.modified = data[1]
            self.MovieHeader.scale = data[2]
            self.MovieHeader.duration = data[3]
        except Exception as e:
            self.log("Error reading movie header: " + str(e))
            self.MovieHeader.duration = 0

    def readBlock(self):
        box = MP4DataBlock()

        try:
            data = self.File.read(4)
            data = self._ensure_bytes(data)  # FIXED
            if not data or len(data) < 4:
                return box
            
            box.size = struct.unpack(">I", data)[0]
            
            boxtype_data = self.File.read(4)
            boxtype_data = self._ensure_bytes(boxtype_data)  # FIXED
            if not boxtype_data or len(boxtype_data) < 4:
                return box
            
            box.boxtype = boxtype_data  # Keep as bytes

            if box.size == 1:
                size_data = self.File.read(8)
                size_data = self._ensure_bytes(size_data)  # FIXED
                if not size_data or len(size_data) < 8:
                    return box
                box.size = struct.unpack(">q", size_data)[0]
                box.size -= 8

            box.size -= 8

            if box.boxtype == b"uuid":
                uuid_data = self.File.read(16)
                uuid_data = self._ensure_bytes(uuid_data)  # FIXED
                if not uuid_data or len(uuid_data) < 16:
                    return box
                box.boxtype = uuid_data
                box.size -= 16
        except Exception as e:
            self.log("Error reading block: " + str(e))
            pass

        return box
