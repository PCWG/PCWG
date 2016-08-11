# -*- coding: utf-8 -*-
"""
Created on Thu Aug 11 12:50:12 2016

@author: Stuart
"""
import os
import os.path

class PathManager(list):
    
    def __init__(self):

        self.base_path = None
        self.base_folder = None
        
        list.__init__(self)
        
    def clone(self):
        
        path_manager = PathManager()
        path_manager.set_base(self.base_path)
        
        for item in self:
            path_manager.append(item.absolute_path)
        
        return path_manager
        
    def contains(self, absolute_path):
        
        for item in self:
            if item.absolute_path == absolute_path:
                return True
                
        return False
            
    def set_base(self, base_path):

        self.base_path = base_path
        self.base_folder = os.path.dirname(os.path.abspath(base_path))

        for item in self:
            item.calculate_paths()
        
    def append_relative(self, relative_path):
        
        if self.base_folder == None:
            raise Exception("Cannot append relative path while base_folder is set to None")
        
        absolute_path = os.path.normpath(os.path.join(self.base_folder, relative_path))
        
        self.append(absolute_path)
        
    def append(self, absolute_path):
        managed_path = ManagedPath(self, absolute_path)
        list.append(self, managed_path)
        return managed_path
    
class ManagedPath:
    
    def __init__(self, base, absolute_path):
        self.base = base
        self.absolute_path = absolute_path
        self.calculate_paths()
    
    def calculate_paths(self):
        if self.base.base_folder == None:
            self.relative_path = None
            self.display_path = self.absolute_path
        else:
            self.relative_path = os.path.relpath(self.absolute_path, self.base.base_folder)   
            self.display_path = self.relative_path
        