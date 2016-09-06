
import Tkinter as tk
import ttk
from tkinterhtml import TkinterHtml
from PIL import Image, ImageTk

images = {}

def test(url):

    image = Image.open("logo.png")
    photo = ImageTk.PhotoImage(image)
    images[url] = photo
    return photo

root = tk.Tk()

html = TkinterHtml(root, fontscale=0.88, imagecmd=test)
vsb = ttk.Scrollbar(root, orient=tk.VERTICAL, command=html.yview)
hsb = ttk.Scrollbar(root, orient=tk.HORIZONTAL, command=html.xview)
html.configure(yscrollcommand=vsb.set)
html.configure(xscrollcommand=hsb.set)

#html.tag("configure", "selection", "-background", "black")

html.grid(row=0, column=0, sticky=tk.NSEW)
vsb.grid(row=0, column=1, sticky=tk.NSEW)
hsb.grid(row=1, column=0, sticky=tk.NSEW)
root.columnconfigure(0, weight=1)
root.rowconfigure(0, weight=1)
#data = urlopen("http://www.wikipedia.org").read().decode()
#html.parse(data)
html.parse("""
<html>
<body>
<h1>Hello world!</h1>
<p>First para</p>
    <ul>
    <li>first list item</li>
    <li>second list item</li>
</ul>
    <img src="logo.png"></img><br />
    <img src="logo.png"></img>
<h1>Hello world!</h1>
</body>
</html>
""")

root.mainloop()