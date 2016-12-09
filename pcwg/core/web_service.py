# -*- coding: utf-8 -*-
"""
Created on Thu Dec 08 16:44:55 2016

@author: Stuart
"""
import re
import json
import urllib2

from ..core.status import Status

class WebService:
    
    def __init__(self,
                 url,
                 power_curve,
                 input_wind_speed_column,
                 normalised_wind_speed_column,
                 turbulence_intensity_column,
                 rotor_wind_seed_ratio_column,
                 has_shear,
                 rows = None):
        
        self.url = url
        self.power_curve = power_curve
        
        self.input_wind_speed_column = input_wind_speed_column
        self.normalised_wind_speed_column = normalised_wind_speed_column
        self.turbulence_intensity_column = turbulence_intensity_column
        self.rotor_wind_seed_ratio_column = rotor_wind_seed_ratio_column
        self.has_shear = has_shear

        self.normalised_wind_speed_re = re.compile(re.escape('<NormalisedWindSpeed>'), re.IGNORECASE)        
        self.turbulence_intensity_re = re.compile(re.escape('<TurbulenceIntensity>'), re.IGNORECASE)
        self.rotor_wind_speed_ratio_re = re.compile(re.escape('<RotorWindSpeedRatio>'), re.IGNORECASE)
        
        self.next_update = 0.1
        self.row = 0
        self.rows = rows
        
    def power(self, row):
        
        wind_speed = row[self.input_wind_speed_column]
        normalised_wind_speed = row[self.normalised_wind_speed_column]
        turbulence_intensity = row[self.turbulence_intensity_column]
                   
        url = self.url
        url = self.normalised_wind_speed_re.sub('{0}'.format(normalised_wind_speed), url)
        url = self.turbulence_intensity_re.sub('{0}'.format(turbulence_intensity), url)
        
        if self.has_shear:
            rotor_wind_speed_ratio = row[self.rotor_wind_seed_ratio_column] 
            url = self.rotor_wind_speed_ratio_re.sub('{0}'.format(rotor_wind_speed_ratio), url)
        
        power = self.power_curve.power(wind_speed)
        response = urllib2.urlopen(url)

        responseText = response.read()   
        data = json.loads(responseText)
        
        deviation = float(data['power_deviation'])
        
        if not self.rows is None:
                        
            if self.rows > 0:
                
                self.row += 1
                
                fraction_complete =  float(self.row) / float(self.rows)
                
                if fraction_complete > self.next_update:
                    Status.add("{0:.0%} Complete".format(fraction_complete))
                    self.next_update += 0.1
            
        return power * (1 + deviation)
        