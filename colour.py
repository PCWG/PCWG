import xlwt

class ColourGradient:

    def __init__(self, minimum, maximum, interval, book):

        self.levels = {}

        self.minimum = minimum
        self.maximum = maximum
        
        dataRange = maximum - minimum
        steps = int(dataRange / interval) + 1
        
        if (steps >= 4):
            steps_4 = steps / 4
        else:
            steps_4 = 1
        
        for i in range(steps):
                        
            if (i <= steps_4):
                red = 255
            elif (i > steps_4 and i <= steps_4 * 2):
                red = 255 - (255 / steps_4) * (i - steps_4)
            elif (i > steps_4 * 2 and i <= steps_4 * 3):
                red = (255 / 2 / steps_4) * (i - steps_4 * 2)
            elif i < steps:
                red = (255 / 2) - (255 / 2 / steps_4) * (i - steps_4 * 3)
            else:
                red = 0

            if (i <= steps_4):
                green = (255 / steps_4) * i
            elif (i > steps_4 and i <= steps_4 * 2):
                green = 255 - (255 / steps_4) * (i - steps_4)
            elif (i > steps_4 * 2 and i <= steps_4 * 3):
                green = (255 / steps_4) * (i - steps_4 * 2)
            else:
                green = 255
                
            if (i <= steps_4):
                blue = 0
            elif (i > steps_4 and i <= steps_4 * 2):
                blue = 0 + (255 / steps_4) * (i - steps_4)
            elif i < steps:
                blue = 255 - (255 / steps_4 / 2) * (i - steps_4 * 2)
            else:
                blue = 0
               
            red = abs(red)
            green = abs(green)
            blue = abs(blue)
            
            if (red > 255): red = 255
            if (green > 255): green = 255
            if (blue > 255): blue = 255

            value = self.roundValue(minimum + i * interval)

            excelIndex = 8 + i
            colourName = "custom_colour_%d" % excelIndex

            xlwt.add_palette_colour(colourName, excelIndex)
            book.set_colour_RGB(excelIndex, red, green, blue)
            
            style = xlwt.easyxf('pattern: pattern solid, fore_colour %s' % colourName, num_format_str='0%')
            
            self.levels[value] = (red, green, blue, value, excelIndex, colourName, style)
          
    def roundValue(self, value):
        return round(value, 2)

    def getStyle(self, value):
        value = max(self.minimum, value)
        value = min(self.maximum, value)
        return self.levels[self.roundValue(value)][6]
