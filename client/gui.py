import tkinter as tk
import tkinter.scrolledtext as scrolledtext
from tkinter.font import Font

from time import sleep
import client.config as cfg

class Gui:
    def __init__(self,enterCallback,closeCallback):
        self.tkRoot = tk.Tk()
        self.tkRoot.iconphoto(False,tk.PhotoImage(file = cfg.windowIconPath))
        self.tkRoot.option_add( "*font", cfg.tkinterFont)

        #font size in pixles
        self.fontSize = Font(family = cfg.tkinterFont[0], size = cfg.tkinterFont[1]).measure("A")

        self.tkRoot.title(cfg.windowName)
        self.generateTkinterObjs()
        self.makeLayout()

        self.lastMessanger=""
        self.prompting=False
        self.promptReturn=""
        #called in textSubmitted
        self.sendToClient = enterCallback

        #used for closing the client if x is hit
        self.closeClient = closeCallback

    def generateTkinterObjs(self):
        self.tkRoot.geometry(cfg.tkinterWinSize)
        
        window=tk.Frame(self.tkRoot)
        window.pack(fill='both',expand=True)
        window.configure(background= cfg.colors["SoftBlack"])


        #main chatbox
        messages=scrolledtext.ScrolledText(window)
        messages.configure(background= cfg.colors["DarkGrey"],foreground=cfg.textColor,borderwidth=0,padx=10,state='disabled',wrap="word")

        textVar=tk.StringVar(window)
        textInput=tk.Entry(window,textvariable=textVar)
        textInput.configure(background= cfg.colors["Grey"],foreground=cfg.textColor,borderwidth=cfg.textInputPad,relief=tk.FLAT)
        
        #binds return key to textEntered
        textInput.bind("<Return>", lambda event: self.textEntered(textVar) )

        #clients online panel
        sidePanel=tk.Text(window)
        sidePanel.configure(background=cfg.colors["SoftBlack"], foreground = cfg.textColor,borderwidth=0,padx=10,pady=5,state='disabled',wrap="word")
        #configure color tags
        for color in cfg.colors.keys():
            messages.tag_config(color, foreground=cfg.colors[color])
            sidePanel.tag_config(color, foreground=cfg.colors[color])

        #configure indent tag
        messages.tag_config("indent",lmargin1=3*self.fontSize,lmargin2=3*self.fontSize)

        self.window=window
        self.window.bind()
        self.messages=messages
        self.textInput = textInput
        self.sidePanel=sidePanel
    
    def makeLayout(self):

        self.messages.grid(row=0,sticky = tk.NSEW)

        self.textInput.grid(row=1,sticky = 'sew')
        self.sidePanel.grid(row=0, column=1,sticky='nsew',rowspan=2)

        self.window.rowconfigure(0,weight=2)
        #self.window.rowconfigure(1,weight=1)
        self.window.columnconfigure(0,weight=1)
        self.window.columnconfigure(1,weight=100,minsize=15*self.fontSize)
    
    #formats based on whos speaking
    def addMessage(self,message,clientDict):
        username = clientDict["username"]
        color = clientDict["color"]
        clientId = clientDict["id"]

        self.messages.configure(state='normal')

        if clientId != self.lastMessanger:
            self.lastMessanger = clientId
            self.messages.insert(tk.END,f"\n{username}:\n", color)

        self.messages.insert(tk.END,f"{message}\n","indent")
        self.messages.configure(state='disabled')

        self.messages.see(tk.END)
        self.textInput.focus_force()


    #username is simply for api compatibility
    def addText(self,text,color=cfg.textColor,endChar="\n"):
        self.lastMessanger=-1

        self.messages.configure(state='normal')
        self.messages.insert(tk.END,f"\n{text}{endChar}", color)
        self.messages.configure(state='disabled')

        self.messages.see(tk.END)
        self.textInput.focus_force()
        
    def updateSidePanel(self,entires,colors):
        self.sidePanel.configure(state='normal')
        self.sidePanel.delete(1.0,tk.END)
        for i,text in enumerate(entires):
            self.sidePanel.insert(tk.END,text+"\n", colors[i])
        self.sidePanel.configure(state='disabled')

    #wrappers for updateSidePanel
    def updateClientsPanel(self,clientsDict,lock):
        lock.acquire()
        entries = [client["username"] for client in clientsDict.values()]
        colors = [client["color"] for client in clientsDict.values()]
        lock.release()
        self.updateSidePanel(entries,colors)
    

    #ment to be run on thread due to long socket pinging time
    #as such it cant update gui and has to create an event
    def updateServerPanel(self,servers,eventQueue):
        ips,names,isOnline = servers.getOnline()
        
        entries = []
        colors = []
        for n,ip in enumerate(ips):
            entries.append(f"{names[n]}:\n{ip}\n")
            colors.append(cfg.onlineColor if isOnline[n] else cfg.offlineColor)
        

        eventQueue.addEvent(self.updateSidePanel,(entries,colors))

    def textEntered(self,strVar):
        text=strVar.get()
        text=text.strip()
        strVar.set("")

        #puts text into prompt return and 
        #signals to prompt method that prompt was
        #submitted
        if self.prompting:
            self.promptReturn=text
            self.prompting = False

        else:
            self.sendToClient(text)


    def prompt(self,text,eventQueue=None,color=cfg.textColor,endChar="\n"):
        self.addText(text,color,endChar)
        self.prompting = True
        
        #made true if application was closed during prompt
        while self.prompting:
            #lowers resource usage
            sleep(cfg.sleepTime)
            try:
                self.tkRoot.update()

                #allows main thread to process events while waiting for prompt return
                if eventQueue:
                    while not eventQueue.empty():
                        eventQueue.triggerEvent()
            except:
                self.prompting=False
                self.closeClient()
        
        #textEntered has placed the input into self.promptReturn
        return self.promptReturn
