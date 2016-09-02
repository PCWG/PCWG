
import Tkinter as tk
import tkFont as tkFont
import ttk as ttk

from ..exceptions.handling import ExceptionHandler


class GridBox(object):

    def __init__(self, master, headers, row, column):

        self.master = master
        self.headers = headers

        self.items_dict = {}

        self.tree = None

        self.container = ttk.Frame(self.master)
        self.container.grid(row=row, column=column, sticky=tk.W+tk.E+tk.N+tk.S)

        self._set_up_tree_widget()
        self._build_tree()

        # create a popup menu
        self.pop_menu = tk.Menu(self.tree, tearoff=0)

        self.pop_menu.add_command(label="New", command=self.new)
        self.pop_menu.add_command(label="Remove", command=self.remove)
        self.pop_menu.add_command(label="Remove All", command=self.remove_all)
        self.pop_menu.add_command(label="Edit", command=self.edit)

        self.pop_menu_add = tk.Menu(self.tree, tearoff=0)
        self.pop_menu_add.add_command(label="New", command=self.new)
        self.pop_menu_add.add_command(label="Remove All", command=self.remove_all)

        self.tree.bind("<Button-2>", self.pop_up)
        self.tree.bind("<Button-3>", self.pop_up)
        
        self.tip = None
        
    def clearTip(self):
        self.setTip("")
    
    def setTipNotRequired(self):
        self.setTip("Not Required")
    
    def setTip(self, text):
        if self.tip != None:
            self.tip['text'] = text

    def item_count(self):
        return len(self.items_dict)

    def pop_up(self, event):

        item = self.tree.identify_row(event.y)

        if item:

            # mouse pointer over item
            self.tree.selection_set(item)        
            self.tree.update()
            self.pop_menu.post(event.x_root, event.y_root)

        else:

            self.pop_menu_add.post(event.x_root, event.y_root)

    def get_selected_key(self):

        selection = self.tree.selection()
        
        if len(selection) > 0:
            return selection[0]
        else:
            return None

    def get_selected(self):

        key = self.get_selected_key()
        
        if key != None:
            return self.items_dict[key]
        else:
            return None

    def new(self):
        pass

    def get_item_values(self, item):
        return {}

    def edit_item(self, item):
        pass

    def remove_all(self):

        keys = self.items_dict.keys()

        for key in keys:
            self.remove_item(key)

    def remove_item(self, key):
        del self.items_dict[key]
        self.tree.delete(key)
             
    def remove(self):
        
        selection = self.get_selected_key()
        
        if selection != None:
            self.remove_item(selection)

    def edit(self):
        
        item = self.get_selected()

        if item != None:
            self.edit_item(item)

    def add_item(self, item):

        values = self.get_tree_values(item)
        key = self.tree.insert('', 'end', values = values)

        self.items_dict[key] = item
        
        self.adjust_width(values)

    def redraw_item(self, key):
        
        item = self.items_dict[key]
        
        values = self.get_tree_values(item)
        
        self.tree.item(key, text='', values=values)

        self.adjust_width(values)
    
    def adjust_width(self, values):

        # adjust column's width if necessary to fit each value
        for ix, val in enumerate(values):
            col_w = tkFont.Font().measure(val)
            if self.tree.column(self.headers[ix],width=None)<col_w:
                self.tree.column(self.headers[ix], width=col_w)
                
    def get_tree_values(self, item):

        values = []
        values_dict = self.get_item_values(item)

        for header in self.headers:
            values.append(values_dict[header])
            
        return values
        
    def add_items(self, items):

        for item in items:
            self.add_item(item)
    
    def get_items(self):
        return self.items_dict.values()

    def double_click(self, event):
        key = self.tree.identify('item',event.x,event.y)
        item = self.items_dict[key]
        self.edit_item(item)

    def _set_up_tree_widget(self):

        tree_container = ttk.Frame(self.container)

        tree_container.grid(row=0, column=0, sticky=tk.W+tk.E+tk.N+tk.S)

        #tree_container.pack(fill='both', expand=True)

        # create a treeview with dual scrollbars
        self.tree = ttk.Treeview(tree_container, columns=self.headers, show="headings")
        
        vsb = ttk.Scrollbar(tree_container, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_container, orient="horizontal", command=self.tree.xview)

        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.grid(column=0, row=0, sticky='nsew')

        vsb.grid(column=1, row=0, sticky='ns')
        hsb.grid(column=0, row=1, sticky='ew')

        tree_container.grid_columnconfigure(0, weight=1)
        tree_container.grid_rowconfigure(0, weight=1)

        self.tree.bind("<Double-1>", self.double_click)

    def get_header_width(self, header):
        return tkFont.Font().measure(header.title()) * self.get_header_scale()

    def get_header_scale(self):
        return 1

    def _build_tree(self):

        for col in self.headers:
            self.tree.heading(col, text=col.title(),
                command=lambda c=col: self.sortby(self.tree, c, 0))
            # adjust the column's width to the header string
            self.tree.column(col, width=self.get_header_width(col))

    def sortby(self, tree, col, descending):
        """sort tree contents when a column header is clicked on"""
        # grab values to sort
        data = [(tree.set(child, col), child) \
            for child in tree.get_children('')]
        # if the data to be sorted is numeric change to float
        #data =  change_numeric(data)
        # now sort the data in place
        data.sort(reverse=descending)
        for ix, item in enumerate(data):
            tree.move(item[1], '', ix)
        # switch the heading so it will sort in the opposite direction
        tree.heading(col, command=lambda col=col: self.sortby(tree, col, \
            int(not descending)))
    
class DialogGridBox(GridBox):

    def __init__(self, master, parent_dialog, row, column):

        self.parent_dialog = parent_dialog

        headers = self.get_headers()

        GridBox.__init__(self, master, headers, row, column)

    def get_headers(self):
        pass

    def get_item_values(self, item):
        pass

    def new_dialog(self, master, parent_dialog, item):
        pass      

    def new(self):

        dialog = self.new_dialog(self.master, self.parent_dialog, None)
        self.add_item(dialog.item)
        
    def edit_item(self, item):                   
                    
        try:
            key = self.get_selected_key() 
            item = self.items_dict[key]
            self.new_dialog(self.master, self.parent_dialog, item)  
            self.redraw_item(key)                             
        except ExceptionHandler.ExceptionType as e:
            self.status.addMessage("ERROR editing item: {0}".format(e))

    def remove(self):
        GridBox.remove(self)
