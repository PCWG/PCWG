# -*- coding: utf-8 -*-
"""
Created on Fri May 13 07:45:29 2016

@author: Stuart
"""

import requests
import re
import urllib
import subprocess
import os.path
import zipfile
from ..core.status import Status
import version as ver

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
            
    def isNewerThan(self, other_version):
        
        if self.tag == None or other_version.tag == None:
            return False
            
        if self.major > other_version.major:
            return True
        elif self.major == other_version.major:
            if self.minor > other_version.minor:
                return True
            elif self.minor == other_version.minor:
                if self.revision > other_version.revision:
                    return True
                else:
                    return False
            else:
                return False
        else:
            return False
                
class Updator:

    prefences_path = "preferences.xml"
    extractor_path = "extractor.exe"
    update_zip = "update.zip"
    
    def __init__(self):

        self.current_version = Version(ver.version)
        self.latest_version = self.get_lastest_version()
        self.is_update_available = self.latest_version.isNewerThan(self.current_version) 

        Status.add("Current Version: {0}".format(self.current_version))
        Status.add("Latest Version: {0}".format(self.latest_version))
        Status.add("Update available: {0}".format(self.is_update_available))
        
        self.version_downloaded = False
        
    def download_latest_version(self):
        
        if not self.is_update_available:
            raise Exception("No update available")
            
        self.download_version(self.latest_version)

        with zipfile.ZipFile(Updator.update_zip) as z:
            if Updator.extractor_path in z.namelist():
                self.extract_file(z, "pcwg_tool/{0}".format(Updator.extractor_path), Updator.extractor_path)
            else:
                Status.add("Cannot update extractor: {0} not found".format(Updator.extractor_path), red = True)
                            
        self.version_downloaded = True
        
    def extract_file(self, z, zip_path, target_path):
        
        with open(target_path, 'wb') as f:
            f.write(z.read(zip_path))
            
    def start_extractor(self):
        
        if not self.version_downloaded:
            raise Exception("No version downloaded")
            
        if not os.path.isfile(Updator.extractor_path):
            raise Exception("{0} not found".format(Updator.extractor_path))
            
        Status.add("Starting extractor")

        subprocess.Popen([Updator.extractor_path])

    def get_lastest_version(self):
        
        try:
            
            r  = requests.get("https://github.com/peterdougstuart/PCWG/releases/latest")
            #note the above will forward to a URL like: https://github.com/peterdougstuart/PCWG/releases/tag/v0.5.13
                    
            data = r.url.split("/")   
            
            return Version(data[-1])
            
        except Exception as e:
    
            Status.add("Cannot determine latest version: {0}".format(e))

            return Version(None)
            
    def download_version(self, version):
        
        try:    
            
            Status.add("Downloading latest version")
            
            zip_file = "pcwg_tool-{0}.zip".format(version.version)
            url = "https://github.com/peterdougstuart/PCWG/releases/download/{0}/{1}".format(version.tag, zip_file)
            print url
            
            urllib.urlretrieve (url, Updator.update_zip)
                
            Status.add("Download complete")
            
        except Exception as e:
    
            Status.add("Cannot download latest version: {0}".format(e))
