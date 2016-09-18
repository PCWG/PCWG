# -*- coding: utf-8 -*-
"""
Created on Mon May 16 21:45:20 2016

@author: stuart
"""

import zipfile
import subprocess
import os
import os.path
import time

class Extractor:

    exe_path = "pcwg_tool.exe"
    update_zip = "update.zip"
    help_doc = "Power Curve Working Group Open Source Tool Overview.docx"
    excel_template = "Share_1_template.xls"
    
    def start_tool(self):
        
        if not os.path.isfile(Extractor.exe_path):
            raise Exception("Cannot start tool: {0} not found.".format(Extractor.exe_path))

        try:
            print "Launching PCWG tool..."
            subprocess.call([Extractor.exe_path])
        except Exception as e:
            raise Exception("Fatal error, could not launch tool: {0}".format(e))
    
    def extract(self):
    
        if not os.path.isfile(Extractor.update_zip):
            raise Exception("Cannot extract: {0} not found.".format(Extractor.update_zip))

        try:            

            print "Extracting..."
                    
            with zipfile.ZipFile(Extractor.update_zip) as z:

                self.extract_file(z, "pcwg_tool/{0}".format(Extractor.exe_path), Extractor.exe_path)
                
                self.extract_file(z, "pcwg_tool/LICENSE", "LICENSE")
                self.extract_file(z, "pcwg_tool/README.md", "README.md")
                self.extract_file(z, "pcwg_tool/{0}".format(Extractor.excel_template), Extractor.excel_template)
                self.extract_file(z, "pcwg_tool/{0}".format(Extractor.help_doc), Extractor.help_doc)

            os.remove(Extractor.update_zip)
            
        except Exception as e:
            
            raise Exception("Fatal error, could not extract: {0}".format(e))

                    
    def extract_file(self, z, zip_path, target_path, attempts = 0):
        
        try:
            with open(target_path, 'wb') as f:
                f.write(z.read(zip_path))
        except Exception as e:
            if attempts < 5:
                print "Cannot exract to {0} (attemp {1}): {2}".format(target_path, attempts, e)
                print "Retrying..."
                time.sleep(5)
                self.extract_file(z, zip_path, target_path, attempts + 1)
            else:
                raise Exception("Cannot exract to {0} (maximum attempts exceeded): {1}".format(target_path))
                
def extract():
    
    time.sleep(5)

    if not os.path.isfile(Extractor.update_zip):
        print "No update found to extract"
        return

    extractor = Extractor()
    
    try:
        extractor.extract()
    except Exception as e:
        print "Cannot extract new version: {0}".format(e)    
        return

    try:
        extractor.start_tool()
    except Exception as e:
        print "Cannot start tool: {0}".format(e)    
        return
        

if __name__ == "__main__":
    extract()