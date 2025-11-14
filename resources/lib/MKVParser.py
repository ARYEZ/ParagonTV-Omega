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
import traceback
import sys

import xbmc
from FileAccess import FileAccess
from Globals import ascii


class MKVParser:
    def log(self, msg, level=xbmc.LOGDEBUG):
        try:
            xbmc.log("script.paragontv-MKVParser: " + ascii(msg), level)
        except:
            xbmc.log("script.paragontv-MKVParser: " + str(msg), level)

    def _ensure_bytes(self, data):
        """Convert string to bytes if needed (Python 3 compatibility) - ULTRA DEFENSIVE"""
        if data is None:
            return b''
        if isinstance(data, bytes):
            return data
        if isinstance(data, str):
            # Try latin1 first (preserves byte values)
            try:
                return data.encode('latin1')
            except:
                pass
            # Try iso-8859-1 (same as latin1)
            try:
                return data.encode('iso-8859-1')
            except:
                pass
            # Last resort - convert each character
            try:
                return bytes([ord(c) & 0xFF for c in data])
            except:
                return b''
        # Handle bytearray
        if isinstance(data, bytearray):
            return bytes(data)
        return b''

    def determineLength(self, filename):
        self.log("determineLength " + filename)

        try:
            self.File = FileAccess.open(filename, "rb", None)
        except:
            self.log("Unable to open the file")
            self.log(traceback.format_exc(), xbmc.LOGERROR)
            return

        size = self.findHeader()

        if size == 0:
            self.log("Unable to find the segment info")
            dur = 0
        else:
            dur = self.parseHeader(size)

        self.log("Duration is " + str(dur))
        return dur

    def parseHeader(self, size):
        duration = 0
        timecode = 0
        fileend = self.File.tell() + size
        datasize = 1
        data = 1

        while self.File.tell() < fileend and datasize > 0 and data > 0:
            data = self.getEBMLId()
            datasize = self.getDataSize()

            if data == 0x2AD7B1:
                timecode = 0

                try:
                    for x in range(datasize):
                        chunk = self.getData(1)
                        chunk = self._ensure_bytes(chunk)
                        if chunk and len(chunk) > 0:
                            timecode = (timecode << 8) + struct.unpack("B", chunk)[0]
                        else:
                            break
                except Exception as e:
                    self.log("Error parsing timecode: " + str(e))
                    timecode = 0

                if duration != 0 and timecode != 0:
                    break
            elif data == 0x4489:
                try:
                    chunk = self.getData(datasize)
                    chunk = self._ensure_bytes(chunk)
                    if chunk and len(chunk) == datasize:
                        if datasize == 4:
                            duration = int(struct.unpack(">f", chunk)[0])
                        else:
                            duration = int(struct.unpack(">d", chunk)[0])
                    else:
                        self.log("Insufficient data for duration, got %d bytes, expected %d" % (len(chunk) if chunk else 0, datasize))
                        duration = 0
                except Exception as e:
                    self.log("Error getting duration in header, size is " + str(datasize) + ": " + str(e))
                    duration = 0

                if timecode != 0 and duration != 0:
                    break
            else:
                try:
                    self.File.seek(datasize, 1)
                except:
                    self.log("Error while seeking")
                    return 0

        if duration > 0 and timecode > 0:
            dur = (duration * timecode) / 1000000000
            return dur

        return 0

    def findHeader(self):
        self.log("findHeader")
        filesize = self.getFileSize()

        if filesize == 0:
            self.log("Empty file")
            return 0

        data = self.getEBMLId()

        # Check for 1A 45 DF A3
        if data != 0x1A45DFA3:
            self.log("Not a proper MKV (got header: 0x%X)" % data if data else "Not a proper MKV (no header)")
            return 0

        datasize = self.getDataSize()

        try:
            self.File.seek(datasize, 1)
        except:
            self.log("Error while seeking")
            return 0

        data = self.getEBMLId()

        # Look for the segment header
        while (
            data != 0x18538067
            and self.File.tell() < filesize
            and data > 0
            and datasize > 0
        ):
            datasize = self.getDataSize()

            try:
                self.File.seek(datasize, 1)
            except:
                self.log("Error while seeking")
                return 0

            data = self.getEBMLId()

        datasize = self.getDataSize()
        data = self.getEBMLId()

        # Find segment info
        while (
            data != 0x1549A966
            and self.File.tell() < filesize
            and data > 0
            and datasize > 0
        ):
            datasize = self.getDataSize()

            try:
                self.File.seek(datasize, 1)
            except:
                self.log("Error while seeking")
                return 0

            data = self.getEBMLId()

        datasize = self.getDataSize()

        if self.File.tell() < filesize:
            return datasize

        return 0

    def getFileSize(self):
        size = 0

        try:
            pos = self.File.tell()
            self.File.seek(0, 2)
            size = self.File.tell()
            self.File.seek(pos, 0)
        except:
            pass

        return size

    def getData(self, datasize):
        data = self.File.read(datasize)
        return data

    def getDataSize(self):
        try:
            data = self.File.read(1)
            data = self._ensure_bytes(data)
            
            if not data or len(data) == 0:
                return 0

            firstbyte = struct.unpack(">B", data)[0]
            datasize = firstbyte
            mask = 0xFFFF

            for i in range(8):
                if datasize >> (7 - i) == 1:
                    mask = mask ^ (1 << (7 - i))
                    break

            datasize = datasize & mask

            if firstbyte >> 7 != 1:
                for i in range(1, 8):
                    chunk = self.File.read(1)
                    chunk = self._ensure_bytes(chunk)
                    if not chunk or len(chunk) == 0:
                        break
                    datasize = (datasize << 8) + struct.unpack(">B", chunk)[0]

                    if firstbyte >> (7 - i) == 1:
                        break
        except Exception as e:
            self.log("Error in getDataSize: " + str(e))
            datasize = 0

        return datasize

    def getEBMLId(self):
        try:
            data = self.File.read(1)
            data = self._ensure_bytes(data)
            
            if not data or len(data) == 0:
                return 0

            firstbyte = struct.unpack(">B", data)[0]
            ID = firstbyte

            if firstbyte >> 7 != 1:
                for i in range(1, 4):
                    chunk = self.File.read(1)
                    chunk = self._ensure_bytes(chunk)
                    if not chunk or len(chunk) == 0:
                        break
                    ID = (ID << 8) + struct.unpack(">B", chunk)[0]

                    if firstbyte >> (7 - i) == 1:
                        break
        except Exception as e:
            self.log("Error in getEBMLId: " + str(e))
            ID = 0

        return ID
