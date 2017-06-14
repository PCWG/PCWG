import math
from scipy import interpolate

class NoneInterpolator:

    def __call__(self, level):
        return None

class ProfileLevels:

    def __init__(self, rotorGeometry, windSpeedLevels, windDirectionLevels=None, upflowLevels=None):

        self.windSpeedLevels = windSpeedLevels
        self.windDirectionLevels = windDirectionLevels
        self.upflowLevels = upflowLevels

        self.rotorGeometry = rotorGeometry

    def getWindSpeedProfile(self, row):
        return self.create_interpolator(row, self.windSpeedLevels)
    
    def getDirectionProfile(self, row):
        return self.create_interpolator(row, self.windDirectionLevels)

    def getUpflowProfile(self, row):
        return self.create_interpolator(row, self.upflowLevels)

    def create_interpolator(self, row, levels_dict):

        if levels_dict is None:
            return NoneInterpolator()

        values = []

        for level in levels_dict:
            
            column = levels_dict[level]

            if not column is None:
                value = row[column]
                values.append((level, value))

        if len(values) >= 3:
            xy = zip(*sorted(values))            
            return interpolate.interp1d(xy[0], xy[1], kind='linear')
        else:
            return NoneInterpolator()

    def findLowestAbove(self, level):

        lowest = None

        for height in self.windSpeedLevels:
            if self.rotorGeometry.within_rotor(height) and height > level:
                if lowest == None or height < lowest:
                    lowest = height

        return lowest

    def findHighestBelow(self, level):

        highest = None

        for height in self.windSpeedLevels:
            if self.rotorGeometry.within_rotor(height) and height < level:
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
        level = self.rotorGeometry.hub_height - self.rotorGeometry.radius + step / 2
        
        for i in range(numberOfRotorLevels):

            self.levels.append(RotorLevel(self.rotorGeometry, level, level - step / 2, level + step / 2))
            level += step

class ProfileLevelsRotor(RotorBase):

    def __init__(self, rotorGeometry, profileLevels):

        RotorBase.__init__(self, rotorGeometry)

        for height in profileLevels.windSpeedLevels:
            if self.rotorGeometry.within_rotor(height):
                
                lowestAbove = profileLevels.findLowestAbove(height)
                highestBelow = profileLevels.findHighestBelow(height)

                if highestBelow is None:
                    bottom = self.rotorGeometry.lower_tip
                else:
                    bottom = (height + highestBelow) / 2

                if lowestAbove is None:
                    top = self.rotorGeometry.upper_tip
                else:
                    top = (height + lowestAbove) / 2              
                
                self.levels.append(RotorLevel(self.rotorGeometry, height, bottom, top))
            
class RotorLevel:

    def __init__(self, rotorGeometry, level, bottom, top):

        self.level = level
        self.bottom = bottom
        self.top = top
        
        self.middle = (self.top + self.bottom) / 2.0
        
        self.area = self.calculateLevelArea(rotorGeometry.hub_height, rotorGeometry.radius, self.middle, top - bottom)
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
    
class HubParameterBase:

    def __init__(self, profileLevels, rotorGeometry):

        self.rotorGeometry = rotorGeometry
        self.profileLevels = profileLevels

class InterpolatedHubDirection:

    def __init__(self, profileLevels, rotorGeometry):        

        HubParameterBase.__init__(self, profileLevels, rotorGeometry)

    def hubDirection(self, row):
        raise Exception("Not implemented")

class InterpolatedHubWindSpeed(HubParameterBase):

    def __init__(self, profileLevels, rotorGeometry):        

        HubParameterBase.__init__(self, profileLevels, rotorGeometry)

    def hubWindSpeed(self, row):

        return self.profileLevels.getWindSpeedProfile(row)(self.rotorGeometry.hub_height)

class PiecewiseHubBase(HubParameterBase):

    def __init__(self, profileLevels, rotorGeometry):        

        HubParameterBase.__init__(self, profileLevels, rotorGeometry)

        self.highestBelow = profileLevels.findHighestBelow(self.rotorGeometry.hub_height)
        self.lowestAbove = profileLevels.findLowestAbove(self.rotorGeometry.hub_height)

class PiecewiseExponentHubWindSpeed(PiecewiseHubBase):

    def __init__(self, profileLevels, rotorGeometry):        

        PiecewiseHubBase.__init__(self, profileLevels, rotorGeometry)
        
    def hubWindSpeed(self, row):

        profile = self.profileLevels.getWindSpeedProfile(row)

        speedAbove = profile(self.lowestAbove)
        speedBelow = profile(self.highestBelow)

        exponent = math.log(speedAbove / speedBelow) / math.log(self.lowestAbove / self.highestBelow)

        return speedBelow * (self.rotorGeometry.hub_height / self.highestBelow) ** exponent

class PiecewiseInterpolationHubDirection(PiecewiseHubBase):

    def __init__(self, profileLevels, rotorGeometry):        

        PiecewiseHubBase.__init__(self, profileLevels, rotorGeometry)

        self.direction_above_col = self.profileLevels.windDirectionLevels[self.lowestAbove]
        self.direction_below_col = self.profileLevels.windDirectionLevels[self.highestBelow]

        self.x = [self.highestBelow, self.lowestAbove]

    def bound_direction(self, direction):

        while direction < 0:
            direction += 360.0

        while direction > 360.0:
            direction -= 360.0

        return direction

    def hubDirection(self, row):

        profile = self.profileLevels.getWindSpeedProfile(row)

        below_direction = row[self.direction_below_col]
        above_direction = row[self.direction_above_col]

        if below_direction is None or above_direction is None:
            return None
        else:

            below_direction = self.bound_direction(below_direction)
            above_direction = self.bound_direction(above_direction)

            if abs(below_direction - above_direction) > 180.0:

                if below_direction > above_direction:
                    below_direction -= 360.0
                else:
                    above_direction -= 360.0

            y = [below_direction, above_direction]
            
            inter = interpolate.interp1d(self.x, y, kind='linear')

            return inter(self.rotorGeometry.hub_height)

class RotorEquivalentWindSpeed:

    def __init__(self, profileLevels, rotor, hubWindSpeedCalculator, rewsVeer, rewsUpflow, exponent):        

        self.profileLevels = profileLevels
        self.rotor = rotor
        self.hubWindSpeedCalculator = hubWindSpeedCalculator
        self.rewsVeer = rewsVeer
        self.rewsUpflow = rewsUpflow
        self.exponent = exponent

        if not profileLevels.windDirectionLevels is None:
            self.hubDirectionCalculator = PiecewiseInterpolationHubDirection(profileLevels, self.rotor.rotorGeometry)
        else:
            self.hubDirectionCalculator = None

        if self.rotor.rotorGeometry.tilt is not None:
            self.tilt_rad = self.to_radians(self.rotor.rotorGeometry.tilt)
        else:
            self.tilt_rad = None

    def rews(self, row):

        speed_profile = self.profileLevels.getWindSpeedProfile(row)
        direction_profile = self.profileLevels.getDirectionProfile(row)
        upflow_profile = self.profileLevels.getUpflowProfile(row)

        equivalentWindSpeed = 0

        if not self.hubDirectionCalculator is None:
            hub_direction = self.hubDirectionCalculator.hubDirection(row)
        else:
            hub_direction = None

        for level in self.rotor.levels:

            speed = speed_profile(level.level)

            if speed is None:
                
                #TODO consider enforcing minimum level count
                #(instead of forcing pre-filters to remove data with any level missing)
                #this would be good fo rnacelle LiDARs (where there is always some data missing)

                raise Exception("Speed cannot be None")

            level_value = self.level_value(speed, level, hub_direction, direction_profile, upflow_profile)

            equivalentWindSpeed += level_value ** self.exponent * level.areaFraction

        equivalentWindSpeed = equivalentWindSpeed ** (1.0 / self.exponent)

        return equivalentWindSpeed
        
    def level_value(self, speed, level, hub_direction, direction_profile, upflow_profile):

        return speed \
                         * self.direction_term(level, hub_direction, direction_profile) \
                         * self.upflow_term(level, speed, upflow_profile)

    def rewsToHubRatio(self, row):

        hub_speed = self.hubWindSpeedCalculator.hubWindSpeed(row)

        return self.rews(row) / hub_speed

    def direction_term(self, level, hub_direction, direction_profile):

        if not self.rewsVeer:
            return 1.0

        direction = direction_profile(level.level)

        if direction is None or hub_direction is None:
            return 1.0
        else:
            direction_rad = self.to_radians(direction)
            hub_direction_rad = self.to_radians(hub_direction)
            return math.cos(direction_rad - hub_direction_rad)

    def upflow_term(self, level, speed, upflow_profile):

        if not self.rewsUpflow:
            return 1.0

        upflow = upflow_profile(level.level)

        if upflow is None or self.tilt_rad is None:
            return 1.0
        else:
            upflow_rad = math.atan2(upflow, speed)
            return math.cos(upflow_rad + self.tilt_rad) / (math.cos(upflow_rad) * math.cos(self.tilt_rad))

    def to_radians(self, direction):
        return direction * math.pi / 180.0

class ProductionByHeight(RotorEquivalentWindSpeed):

    def __init__(self, profileLevels, rotor, hubWindSpeedCalculator, power_curve):        

        RotorEquivalentWindSpeed.__init__(self, profileLevels, rotor, hubWindSpeedCalculator, False, False, 1.0)

        self.power_curve = power_curve

    def level_value(self, speed, level, hub_direction, direction_profile, upflow_profile):
        return self.power_curve.power(speed)

    def calculate(self, row):
        
        hub_speed = self.hubWindSpeedCalculator.hubWindSpeed(row)
        hub_power = self.power_curve.power(hub_speed)

        return self.rews(row) - hub_power
