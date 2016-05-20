# -*- coding: utf-8 -*-
"""
Created on Fri May 13 07:45:29 2016

@author: Stuart
"""
import os
import os.path
import subprocess
from shutil import copyfile
import xml.dom.minidom
import tkMessageBox
from Tkinter import Tk
import requests
import re
import urllib
import zipfile

source_core = "core.lib"
target_core = "pcwg_core.exe"
launcher = "pcwg_tool.exe"
launcher_update = "{0}.update".format(launcher)

class Version:
    
    def __init__(self, tag):
        
        if tag != None:

            self.tag = tag.lower()
            self.version = re.findall("\d+\.?\d+\.?\d+", self.tag)[0].lower()
            
            data = self.version.split(".")
            
            self.major = data[0]
            
            if len(data) > 1:
                self.minor = data[1]
            else:
                self.minor = None
                
            if len(data) > 2:
                self.revision = data[2]
            else:
                self.revision = None

        else:

            self.tag = None
            self.version = None
            self.major = None
            self.minor = None
            self.revision = None
            
    def __str__(self):
        if self.tag != None:
            return self.tag
        else:
            return "Unknown"
            
    def isNewerThan(self, version):
        
        if self.tag == None or version.tag == None:
            return False
            
        if self.major > version.major:
            return True
        elif self.major == version.major:
            if self.minor > version.minor:
                return True
            elif self.minor == version.minor:
                if self.revision > version.revision:
                    return True
                else:
                    return False
            else:
                return False
        else:
            return False
        
def get_last_opened_version():
    
    try:

        prefences_path = "preferences.xml"
        
        if not os.path.isfile(prefences_path):
            print "Cannot determine last opened version: {0} not found".format(prefences_path)
            return Version(None)
            
        namespace = "http://www.pcwg.org"
        doc = xml.dom.minidom.parse(prefences_path)
        root = doc.getElementsByTagNameNS(namespace, "Preferences")[0] 
        nodes = root.getElementsByTagNameNS(namespace, "VersionLastOpened")
 
        if len(nodes) < 1:
            print "Cannot determine last opened version: VersionLastOpened not found in {0}".format(prefences_path)
            return Version(None)
            
        value = nodes[0].firstChild.data

        return Version(value)

    except None as e:
        print "Cannot determine last opened version: {0}".format(e)

def get_lastest_version():
    
    try:
        
        r  = requests.get("https://github.com/peterdougstuart/PCWG/releases/latest")
        #note the above will forward to a URL like: https://github.com/peterdougstuart/PCWG/releases/tag/v0.5.13
                
        data = r.url.split("/")   
        
        return Version(data[-1])
        
    except Exception as e:

        print "Cannot determine latest version: {0}".format(e)
        return Version(None)
        
def download_version(version):
    
    try:    
        
        print "Downloading latest version"
        
        zip_file = "pcwg_tool-{0}.zip".format(version.version)
        url = "https://github.com/peterdougstuart/PCWG/releases/download/{0}/{1}".format(version.tag, zip_file)
    
        urllib.urlretrieve (url, zip_file)

        print "Extracting"
        
        with zipfile.ZipFile(zip_file) as z:
            with open(source_core, 'wb') as f:
                f.write(z.read("pcwg_tool/{0}".format(source_core)))

        with zipfile.ZipFile(zip_file) as z:
            with open(launcher_upgrade, 'wb') as f:
                f.write(z.read("pcwg_tool/{0}".format(launcher)))
                
        os.remove(zip_file)
        
    except Exception as e:

        print "Cannot download latest version: {0}".format(e)
        
last_opened_version = get_last_opened_version()
latest_version = get_lastest_version()

print "Version Last Opened: {0}".format(last_opened_version)
print "Latest Version: {0}".format(latest_version)

root = Tk()

if latest_version.isNewerThan(last_opened_version):
    if tkMessageBox.askyesno("New Version Available", "A new version is available (current version {0}), do you want to upgrade to {1}?".format(last_opened_version, latest_version)):
        download_version(latest_version)

root.destroy()

if os.path.isfile(target_core):
    try:
        os.remove(target_core)
    except Exception as e:
        print "Warning could not remove old core file: {0}".format(e)

try:
    copyfile(source_core, target_core)
except Exception as e:
    print "Warning copy core file to target: {0}".format(e)

try:
    print "Launching PCWG tool"
    subprocess.call([target_core])

except Exception as e:
    print "Fatal error, could not launch tool: {0}".format(e)

try:
    os.remove(target_core)
except Exception as e:
    print "Could not clean up: {0}".format(e)
    
print "Done"

try:
    print "Upgrading launcher"
    subprocess.call([target_core])
except Exception as e:
    print "Fatal error, could not upgrade launcher: {0}".format(e)
