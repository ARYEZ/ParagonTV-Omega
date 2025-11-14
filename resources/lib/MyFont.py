# modules
import os
import sys
import xml.etree.ElementTree as ET

import xbmc
import xbmcaddon
import xbmcvfs

ADDON = xbmcaddon.Addon(id="script.paragontv")
SkinPath = xbmcvfs.translatePath("special://skin")
ScriptPath = xbmcvfs.translatePath(ADDON.getAddonInfo("path"))
SourceFontPath = os.path.join(ScriptPath, "resources", "fonts", "Lato-Regular.ttf")
ListDir = os.listdir(SkinPath)


# Python 3.10+ compatibility: XMLTreeBuilder was removed
# Use XMLParser with TreeBuilder instead
try:
    # Try old method (Python 3.9 and earlier)
    class PCParser(ET.XMLTreeBuilder):
        def __init__(self):
            ET.XMLTreeBuilder.__init__(self)
            self._parser.CommentHandler = self.handle_comment

        def handle_comment(self, data):
            self._target.start(ET.Comment, {})
            self._target.data(data)
            self._target.end(ET.Comment)
except AttributeError:
    # Python 3.10+: XMLTreeBuilder removed, use TreeBuilder
    class PCParser(ET.TreeBuilder):
        def __init__(self):
            super().__init__()
            # Comment handling for Python 3.10+
            self.comment_handler = None

        def handle_comment(self, data):
            # In Python 3.10+, comments are handled differently
            # Create a comment element
            elem = ET.Comment(data)
            return elem


def getFontsXML():
    fontxml_paths = []
    try:
        for item in ListDir:
            item = os.path.join(SkinPath, item)
            if os.path.isdir(item):
                font_xml = os.path.join(item, "Font.xml")
                if os.path.exists(font_xml):
                    fontxml_paths.append(font_xml)
    except:
        pass
    return fontxml_paths


def isFontInstalled(fontxml_path, fontname):
    name = "<name>%s</name>" % fontname
    try:
        with open(fontxml_path, "r", encoding='utf-8') as f:
            content = f.read()
        return name in content
    except:
        return False


def copyFont(SourceFontPath, SkinPath):
    dest = os.path.join(SkinPath, "fonts", "Lato-Regular.ttf")
    if os.path.exists(dest):
        return
    xbmcvfs.copy(SourceFontPath, dest)


def getSkinRes():
    SkinRes = "720p"
    SkinResPath = os.path.join(SkinPath, SkinRes)
    if not os.path.exists(SkinResPath):
        SkinRes = "1080i"
    return SkinRes


def addFont(fontname, filename, size, style=""):
    try:
        reload_skin = False
        fontxml_paths = getFontsXML()
        if fontxml_paths:
            for fontxml_path in fontxml_paths:
                if not isFontInstalled(fontxml_path, fontname):
                    parser = PCParser()
                    tree = ET.parse(fontxml_path, parser=parser)
                    root = tree.getroot()
                    for sets in list(root):  # Use list(root) instead of getchildren()
                        # Find all font elements
                        font_elements = sets.findall("font")
                        if font_elements:
                            font_elements[-1].tail = "\n\t\t"
                        new = ET.SubElement(sets, "font")
                        new.text, new.tail = "\n\t\t\t", "\n\t"
                        subnew1 = ET.SubElement(new, "name")
                        subnew1.text = fontname
                        subnew1.tail = "\n\t\t\t"
                        subnew2 = ET.SubElement(new, "filename")
                        subnew2.text = (filename, "Arial.ttf")[
                            sets.attrib.get("id") == "Arial"
                        ]
                        subnew2.tail = "\n\t\t\t"
                        subnew3 = ET.SubElement(new, "size")
                        subnew3.text = size
                        subnew3.tail = "\n\t\t\t"
                        last_elem = subnew3
                        if style in ["normal", "bold", "italics", "bolditalics"]:
                            subnew4 = ET.SubElement(new, "style")
                            subnew4.text = style
                            subnew4.tail = "\n\t\t\t"
                            last_elem = subnew4
                        reload_skin = True
                        last_elem.tail = "\n\t\t"
                    tree.write(fontxml_path)
                    reload_skin = True
    except:
        pass

    if reload_skin:
        copyFont(SourceFontPath, SkinPath)
        xbmc.executebuiltin("XBMC.ReloadSkin()")
        return True

    return False
