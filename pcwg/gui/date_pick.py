
#based on code by : Camilo Olarte|colarte@telesat.com.co|Sept.2003

import sys
import string
import calendar
import Tkinter as tk
import time
import datetime
import dateutil

from tk_simple_dialog import Dialog

from ..core.status import Status

class ParseClipBoard:

    def __init__(self, master, dateFormat, callback):
        self.master = master
        self.dateFormat = dateFormat
        self.callback = callback

    def __call__(self):
            
        try:
                
            clipboard = self.master.selection_get(selection = "CLIPBOARD")
            
            if len(clipboard) > 0:

                try:                                        
                    date = datetime.datetime.strptime(clipboard, self.dateFormat)
                except Exception as e:
                    try:
                        date = dateutil.parser.parse(clipboard)
                    except Exception as e:
                        date = None
                        Status.add("Can't parse clipboard (%s)" % e.message)

                if date != None:
                    self.callback(date)
                                
        except Exception as e:
                Status.add("Can't parse clipboard (%s)" % e.message)

class Calendar(Dialog):

    DATE_FORMAT = "%Y-%m-%d %H:%M"

    FONT = ("Times", 12)

    def __init__ (self, master, selected_date = None, date_format = None):

        today = datetime.date.today()
        self.empty_date = datetime.datetime(year=today.year, month=today.month, day=today.day)

        self.selected_date = selected_date

        if date_format is None:
            self.date_format = Calendar.DATE_FORMAT
        else:
            self.date_format = date_format

        Dialog.__init__(self, master, "Calendar")
        
    def body(self, master):

        self.canvas =tk.Canvas(master, width =200, height =180,
          relief =tk.RIDGE, background ="white", borderwidth =1)

        self.year_label = tk.Label(master, font=Calendar.FONT, background="white")
        self.year_label.place(x=105, y=10)

        self.month_label = tk.Label(master, font=Calendar.FONT, background="white")
        self.month_label.place(x=105, y=30)

        self.base_button_tag = "Arrow"
        self.base_number_tag = "Number"

        self.left_year_tag = "LeftYear"
        self.right_year_tag = "RightYear"
        self.left_month_tag = "LeftMonth"
        self.right_month_tag = "RightMonth"

        self.create_left_arrow(self.canvas, 60, 23, (self.base_button_tag, self.left_year_tag))
        self.create_right_arrow(self.canvas, 170, 23, (self.base_button_tag, self.right_year_tag))
        self.create_left_arrow(self.canvas, 60, 43, (self.base_button_tag, self.left_month_tag))
        self.create_right_arrow(self.canvas, 170, 43, (self.base_button_tag, self.right_month_tag))

        self.canvas.pack (expand =1, fill =tk.BOTH)
        self.canvas.tag_bind (self.base_button_tag, "<ButtonRelease-1>", self.on_click)
        self.canvas.tag_bind (self.base_button_tag, "<Enter>", self.on_mouse_over)
        self.canvas.tag_bind (self.base_button_tag, "<Leave>", self.on_mouse_out)   

        self.time_frame = tk.Frame(master)
        self.time_frame.pack()

        if self.selected_date is None:
            hour = 0
        else:
            hour = self.selected_date.hour

        self.hour_var = tk.StringVar(self.time_frame, "{0:02}".format(hour))
        self.hour_option = apply(tk.OptionMenu, (self.time_frame, self.hour_var) + tuple('{:02}'.format(x) for x in range(24)))
        self.hour_option.grid(row=1, column=1, sticky=tk.W)
        self.hour_var.trace('w', self.update_time)

        if self.selected_date is None:
            minute = 0
        else:
            minute = self.selected_date.minute

        self.minute_var = tk.StringVar(self.time_frame, "{0:02}".format(minute))
        self.minute_option = apply(tk.OptionMenu, (self.time_frame, self.minute_var) + tuple('{:02}'.format(x * 10) for x in range(6)))
        self.minute_option.grid(row=1, column=2, sticky=tk.E)
        self.minute_var.trace('w', self.update_time)

        #date label and clear button
        self.date_frame = tk.Frame(master)
        self.date_frame.pack()

        self.date_label = tk.Label(self.date_frame)
        self.date_label.grid(row=1, column=1, sticky=tk.W)

        self.clear_button = tk.Button(self.date_frame, text="X", command = self.click_clear)
        self.clear_button.grid(row=1, column=2, sticky=tk.E)

        self.parse_button = tk.Button(self.date_frame, text="Parse", command = ParseClipBoard(master, self.date_format, self.set_parse))
        self.parse_button.grid(row=1, column=3, sticky=tk.E)

        self.radius = 10
        self.circle_hover = self.create_circle(self.canvas, 0, 0, self.radius, outline="#DDD", width=4)
        self.canvas.itemconfigure(self.circle_hover, state='hidden')

        self.circle_selected = self.create_circle(self.canvas, 0, 0, self.radius, outline="#00D", width=3)
        self.canvas.itemconfigure(self.circle_selected, state='hidden')

        self.fill_calendar()
        self.update_labels()

    def set_parse(self, date):

        if not date is None:
            self.selected_date = date
            self.update_labels()
            self.fill_calendar()

    def click_clear(self):

        self.hour_var.set('00')        
        self.minute_var.set('00')

        self.selected_date = None
        self.hide(self.circle_selected)

        self.update_labels()
        self.fill_calendar()

    def update_time(self, *args):

        if not self.selected_date is None:
    
            self.selected_date = datetime.datetime(year=self.selected_date.year,
                                                    month=self.selected_date.month,
                                                    day=self.selected_date.day,
                                                    hour=int(self.hour_var.get()),
                                                    minute=int(self.minute_var.get()))

        self.update_labels()

    def update_labels(self):

        if not self.selected_date is None:
            display_date = self.selected_date
            self.date_label.configure(text=self.selected_date.strftime(self.date_format))
        else:
            display_date = self.empty_date
            self.date_label.configure(text="DATE NOT SET")

        self.month_label.configure(text=display_date.strftime("%b"))
        self.year_label.configure(text=display_date.strftime("%Y"))

    def create_right_arrow(self, canv, x, y, strtagname):
        canv.create_polygon(x,y, [[x+0,y-5], [x+10, y-5] , [x+10,y-10] , 
        [x+20,y+0], [x+10,y+10] , [x+10,y+5] , [x+0,y+5]],
        tags = strtagname , fill="blue", width=0)

    def create_left_arrow(self, canv, x, y, strtagname):
        canv.create_polygon(x,y, [[x+10,y-10], [x+10, y-5] , [x+20,y-5] , 
        [x+20,y+5], [x+10,y+5] , [x+10,y+10] ],
        tags = strtagname , fill="blue", width=0)

    def on_click(self,event):
        
        owntags =self.canvas.gettags(tk.CURRENT)

        if self.selected_date is None:
            current_date = self.empty_date
        else:
            current_date = self.selected_date

        if self.right_year_tag in owntags:
            
            year_shift = 1
            month_shift = 0

        elif self.left_year_tag in owntags:
            
            year_shift = -1
            month_shift = 0

        elif self.right_month_tag in owntags:

            if current_date.month < 12:
                year_shift = 0
                month_shift = 1
            else:
                year_shift = 1
                month_shift = -11

        elif self.left_month_tag in owntags:

            if current_date.month > 1:
                year_shift = 0
                month_shift = -1
            else:
                year_shift = -1
                month_shift = 11

        if not self.selected_date is None:

            self.selected_date = datetime.datetime(year=current_date.year + year_shift,
                                                    month=current_date.month + month_shift,
                                                    day=current_date.day,
                                                    hour=current_date.hour,
                                                    minute=current_date.minute)  
        else:

            self.empty_date = datetime.datetime(year=self.empty_date.year + year_shift,
                                                    month=self.empty_date.month + month_shift,
                                                    day=self.empty_date.day,
                                                    hour=self.empty_date.hour,
                                                    minute=self.empty_date.minute)  

        self.update_labels()
        self.hide(self.circle_selected)
        self.fill_calendar()       
    
    def fill_calendar(self):

        init_x = 40
        y = 70

        step_x = 27
        step_y = 20

        self.canvas.delete(self.base_number_tag)
        self.canvas.update()

        if self.selected_date is None:
            month_calender = calendar.monthcalendar(self.empty_date.year, self.empty_date.month)   
        else:
            month_calender = calendar.monthcalendar(self.selected_date.year, self.selected_date.month)   

        for row in month_calender:
            
            x = init_x 

            for item in row:    
            
                if item > 0:

                    self.canvas.create_text(x,
                                            y,
                                            text=str(item), 
                                            font=Calendar.FONT,
                                            tags=(self.base_number_tag, item))   

                    if not self.selected_date is None:
                        if self.selected_date.day == item:
                            self.move_to(self.circle_selected, (x, y))
                            self.show(self.circle_selected)

                x+= step_x
            
            y += step_y

        self.canvas.tag_bind(self.base_number_tag, "<ButtonRelease-1>", self.click_number)
        self.canvas.tag_bind(self.base_number_tag, "<Enter>", self.on_mouse_over)
        self.canvas.tag_bind(self.base_number_tag, "<Leave>", self.on_mouse_out)   

    def click_number(self,event):

        owntags =self.canvas.gettags(tk.CURRENT)
        
        for day_tag in owntags:

            if not day_tag in ["current", self.base_number_tag]:

                hour = int(self.hour_var.get())
                minute = int(self.minute_var.get())

                if not self.selected_date is None:

                    self.selected_date = datetime.datetime(year = self.selected_date.year,
                                                        month = self.selected_date.month,
                                                        day = int(day_tag),
                                                        hour = hour,
                                                        minute = minute)

                else:

                    self.selected_date = datetime.datetime(year = self.empty_date.year,
                                                        month = self.empty_date.month,
                                                        day = int(day_tag),
                                                        hour = hour,
                                                        minute = minute)

                self.update_labels()

                self.move_to_current(self.circle_selected)
                self.show(self.circle_selected)
                
                self.canvas.update()

    def on_mouse_over(self, event):

        tags =self.canvas.gettags(tk.CURRENT)
    
        if self.base_button_tag in tags:
            self.canvas.itemconfigure(tk.CURRENT, fill='#DDD')
            return

        self.move_to_current(self.circle_hover)
        self.show(self.circle_hover)
        self.canvas.update()

    def on_mouse_out(self, event):

        tags =self.canvas.gettags(tk.CURRENT)
    
        if self.base_button_tag in tags:
            self.canvas.itemconfigure(tk.CURRENT, fill='blue')
            return

        self.hide(self.circle_hover)
        self.canvas.update()

    def show(self, tag):
        self.canvas.itemconfigure(tag, state='normal')

    def hide(self, tag):
        self.canvas.itemconfigure(tag, state='hidden')

    def move_to_tag(self, tag, target_tag):
        self.move_to(tag, self.canvas.coords(target_tag))

    def move_to_current(self, tag):
        self.move_to_tag(tag, tk.CURRENT)

    def move_to(self, tag, new_coords):
        old_coords = self.canvas.coords(tag)
        self.canvas.move(tag, new_coords[0] - old_coords[0] - self.radius, new_coords[1] - old_coords[1] - self.radius)

    def create_circle(self, canvas, x, y, r, **kwargs):
        return canvas.create_oval(x-r, y-r, x+r, y+r, **kwargs)

class MainFrame(tk.Frame):

    def __init__(self, master):
        
        self.parent = master
        tk.Frame.__init__(master)
        
        testBtn = tk.Button(master, text = 'getdate',command = self.launch_calendar)
        testBtn.pack()

        self.date =  None
        self.date_label = tk.Label(master, text="NOT SET")
        self.date_label.pack()

    def launch_calendar(self):
        
        calendar = Calendar(self.parent)
        self.date = calendar.selected_date
        self.date_label.configure(text = str(self.date))

if __name__ == '__main__':
    root =tk.Tk()
    root.title ("Calendar")
    Frm = tk.Frame(root)
    MainFrame(Frm)
    Frm.pack()
    root.mainloop()