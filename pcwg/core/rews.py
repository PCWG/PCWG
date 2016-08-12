import math
from scipy import interpolate

class ProfileLevels:

    def __init__(self, rotorGeometry, windSpeedLevels):

        self.windSpeedLevels = windSpeedLevels
        self.rotorGeometry = rotorGeometry

    def getWindSpeedProfile(self, row):

        values = []

        for level in self.windSpeedLevels:
            
            column = self.windSpeedLevels[level]
            speed = row[column]
            
            values.append((level, speed))

        xy = zip(*sorted(values))
        
        return interpolate.interp1d(xy[0], xy[1], kind='linear')
        
    def findLowestAbove(self, level):

        lowest = None

        for height in self.windSpeedLevels:
            if self.rotorGeometry.withinRotor(height) and height > level:
                if lowest == None or height < lowest:
                    lowest = height

        return lowest

    def findHighestBelow(self, level):

        highest = None

        for height in self.windSpeedLevels:
            if self.rotorGeometry.withinRotor(height) and height < level:
                if highest == None or height > highest:
                    highest = height

        return highest    
		
class RotorBase:

    def __init__(self, rotorGeometry):

        self.rotorGeometry = rotorGeometry
        self.levels = []

    def __str__(self):

        value = "Level\tBottom\tTop\tArea\tArea Fraction\n"

        for level in self.levels:
            value += "%0.2f\t%0.2f\t%0.2f\t%0.2f\t%0.2f%%\n" % (level.level, level.bottom, level.top, level.area, (level.areaFraction * 100.0))

        return value
    
class EvenlySpacedRotor(RotorBase):

    def __init__(self, rotorGeometry, numberOfRotorLevels):

        RotorBase.__init__(self, rotorGeometry)        
        
        if (numberOfRotorLevels % 2) != 1:
            raise Exception("Number of levels must be odd") 
        
        step = self.rotorGeometry.diameter / numberOfRotorLevels
        level = self.rotorGeometry.hubHeight - self.rotorGeometry.radius + step / 2
        
        for i in range(numberOfRotorLevels):

            self.levels.append(RotorLevel(self.rotorGeometry, level, level - step / 2, level + step / 2))
            level += step

class ProfileLevelsRotor(RotorBase):

    def __init__(self, rotorGeometry, profileLevels):

        RotorBase.__init__(self, rotorGeometry)

        for height in profileLevels.windSpeedLevels:
            if self.rotorGeometry.withinRotor(height):
                
                lowestAbove = profileLevels.findLowestAbove(height)
                highestBelow = profileLevels.findHighestBelow(height)

                if highestBelow == None:
                    bottom = self.rotorGeometry.lowerTip
                else:
                    bottom = (height + highestBelow) / 2

                if lowestAbove == None:
                    top = self.rotorGeometry.upperTip
                else:
                    top = (height + lowestAbove) / 2              
                
                self.levels.append(RotorLevel(self.rotorGeometry, height, bottom, top))
            
class RotorLevel:

    def __init__(self, rotorGeometry, level, bottom, top):

        self.level = level
        self.bottom = bottom
        self.top = top
        
        self.middle = (self.top + self.bottom) / 2.0
        
        self.area = self.calculateLevelArea(rotorGeometry.hubHeight, rotorGeometry.radius, self.middle, top - bottom)
        self.areaFraction  = self.area / rotorGeometry.area
        
    def calculateLevelArea(self, hubHeight, radius, level, step):

        a1 = self.calculateArea(hubHeight, radius, level, step)
            
        if level < hubHeight:
            a2 = self.calculateArea(hubHeight, radius, level - step, step)
        else:
            a2 = self.calculateArea(hubHeight, radius, level + step, step)
        
        return a1 - a2

    def calculateArea(self, hubHeight, radius, level, step):

        bottom = level - step / 2
        top = level + step / 2

        rotorBottom = hubHeight - radius
        rotorTop = hubHeight + radius
        
        if level > rotorTop or level < rotorBottom:

            return 0.0
        
        else:
            
            if level < hubHeight:
                adjacement = hubHeight - top        
            else:
                adjacement = bottom - hubHeight

            cosHalfAngle = adjacement / radius

            angle = math.acos(cosHalfAngle) * 2.0
 
            return 0.5 * (angle - math.sin(angle)) * radius ** 2
    
class HubWindSpeedBase:

    def __init__(self, profileLevels, rotorGeometry):

        self.rotorGeometry = rotorGeometry
        self.profileLevels = profileLevels

class InterpolatedHubWindSpeed(HubWindSpeedBase):

    def __init__(self, profileLevels, rotorGeometry):        

        HubWindSpeedBase.__init__(self, profileLevels, rotorGeometry)

    def hubWindSpeed(self, row):

        return self.profileLevels.getWindSpeedProfile(row)(self.rotorGeometry.hubHeight)  

class PiecewiseExponentHubWindSpeed(HubWindSpeedBase):

    def __init__(self, profileLevels, rotorGeometry):        

        HubWindSpeedBase.__init__(self, profileLevels, rotorGeometry)

        self.highestBelow = profileLevels.findHighestBelow(self.rotorGeometry.hubHeight)
        self.lowestAbove = profileLevels.findLowestAbove(self.rotorGeometry.hubHeight)
        
    def hubWindSpeed(self, row):

        profile = self.profileLevels.getWindSpeedProfile(row)

        speedAbove = profile(self.lowestAbove)
        speedBelow = profile(self.highestBelow)

        exponent = math.log(speedAbove / speedBelow) / math.log(self.lowestAbove / self.highestBelow)

        return speedBelow * (self.rotorGeometry.hubHeight / self.highestBelow) ** exponent

class RotorEquivalentWindSpeed:

    def __init__(self, profileLevels, rotor):        

        self.profileLevels = profileLevels
        self.rotor = rotor
                        
    def rotorWindSpeed(self, row):

        profile = self.profileLevels.getWindSpeedProfile(row)
        
        equivalentWindSpeed = 0

        for level in self.rotor.levels:
            windSpeed = profile(level.level)
            equivalentWindSpeed += windSpeed ** 3.0 * level.areaFraction
            
        return equivalentWindSpeed ** (1.0 / 3.0)
