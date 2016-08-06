
import Tkinter as tk
import tkFont as tkFont
import ttk as ttk
import tkMessageBox

class TestClass(object):

    def __init__(self, first_name, last_name):
        self.first_name = first_name
        self.last_name = last_name

    def get_values(self):

        values = {}
        values['First Name'] = self.first_name
        values['Last Name'] = self.last_name

        return values

class GridBox(object):

    def __init__(self, parent, headers, label = None):

        self.parent = parent
        self.headers = headers
        self.items = {}

        self.tree = None

        self.parent.rowconfigure(0, weight=0)
        self.parent.rowconfigure(1, weight=1)
        self.parent.columnconfigure(0, weight=1)

        if label != None:
            self.label = ttk.Label(self.parent, text = label, font = "Helvetica 14 bold")
            self.label.grid(row=0, column=0, sticky=tk.W+tk.E)

        self.container = ttk.Frame(self.parent)
        self.container.grid(row=1, column=0, sticky=tk.W+tk.E+tk.N+tk.S)

        self.container.rowconfigure(0, weight=1)
        self.container.columnconfigure(0, weight=1)
        self.container.columnconfigure(1, weight=0)

        self._setup_widgets()
        self._build_tree()

        # create a popup menu
        self.pop_menu = tk.Menu(self.tree, tearoff=0)
        self.pop_menu.add_command(label="Add", command=self.add)
        self.pop_menu.add_command(label="Remove", command=self.remove)
        self.pop_menu.add_command(label="Edit", command=self.edit)

        self.pop_menu_add = tk.Menu(self.tree, tearoff=0)
        self.pop_menu_add.add_command(label="Add", command=self.add)

        self.tree.bind("<Button-2>", self.pop_up)
        self.tree.bind("<Button-3>", self.pop_up)

    def pop_up(self, event):

        item = self.tree.identify_row(event.y)

        if item:

            # mouse pointer over item
            self.tree.selection_set(item)        
            self.tree.update()
            self.pop_menu.post(event.x_root, event.y_root)

        else:

            self.pop_menu_add.post(event.x_root, event.y_root)

    def get_selected(self):

        selection = self.tree.selection()
        
        if len(selection) > 0:
            return selection[0] ## get selected item
        else:
            return None

    def add(self):
        pass

    def edit_item(self, item):
        pass
        
    def remove(self):
        
        selection = self.get_selected()
        
        if selection != None:
            del self.items[selection]
            self.tree.delete(selection)

    def edit(self):
        
        selection = self.get_selected()
        item = self.items[selection]

        self.edit_item(item)

    def double_click(self, event):
        self.edit()

    def _setup_widgets(self):

        self._set_up_tree_widget()

        button_container = ttk.Frame(self.container)

        button_container.grid(row=0, column=1, sticky=tk.W)

        self.add_button = tk.Button(button_container, text="Add", command=self.add)
        self.add_button.pack()

        self.remove_button = tk.Button(button_container, text="Remove", command=self.remove)
        self.remove_button.pack()

        self.edit_button = tk.Button(button_container, text="Edit", command=self.edit)
        self.edit_button.pack()

    def _set_up_tree_widget(self):

        tree_container = ttk.Frame(self.container)

        tree_container.grid(row=0, column=0, sticky=tk.W+tk.E+tk.N+tk.S)

        #tree_container.pack(fill='both', expand=True)

        # create a treeview with dual scrollbars
        self.tree = ttk.Treeview(columns=self.headers, show="headings")
        vsb = ttk.Scrollbar(orient="vertical",
            command=self.tree.yview)
        hsb = ttk.Scrollbar(orient="horizontal",
            command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set,
            xscrollcommand=hsb.set)
        self.tree.grid(column=0, row=0, sticky='nsew', in_=tree_container)
        vsb.grid(column=1, row=0, sticky='ns', in_=tree_container)
        hsb.grid(column=0, row=1, sticky='ew', in_=tree_container)
        tree_container.grid_columnconfigure(0, weight=1)
        tree_container.grid_rowconfigure(0, weight=1)

        self.tree.bind("<Double-1>", self.double_click)

    def _build_tree(self):
        
        for col in self.headers:
            self.tree.heading(col, text=col.title(),
                command=lambda c=col: self.sortby(self.tree, c, 0))
            # adjust the column's width to the header string
            self.tree.column(col,
                width=tkFont.Font().measure(col.title()))

    def add_item(self, item):

        values = []
        values_dict = item.get_values()

        for header in self.headers:
            values.append(values_dict[header])

        key = self.tree.insert('', 'end', values=values)
        self.items[key] = item

        # adjust column's width if necessary to fit each value
        for ix, val in enumerate(values):
            col_w = tkFont.Font().measure(val)
            if self.tree.column(self.headers[ix],width=None)<col_w:
                self.tree.column(self.headers[ix], width=col_w)

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
        tree.heading(col, command=lambda col=col: sortby(tree, col, \
            int(not descending)))

if __name__ == "__main__":

    # the test data ...
    header = ['First Name', 'Last Name']

    root = tk.Tk()

    box = GridBox(root, header, label='Title')

    box.add_item(TestClass("Peter", "Stuart"))

    root.mainloop()