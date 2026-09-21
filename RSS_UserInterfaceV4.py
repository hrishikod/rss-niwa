# -*- coding: utf-8 -*-
"""
Created on Mon May  4 10:55:56 2020

RSS model GUI - reads in the RSS model code and performs the analysis

@author: daviesaf
"""

import tkinter as tk
from tkinter import messagebox
from tkinter import ttk

import os
import numpy as np
import pandas as pd
import xlsxwriter
import geopandas as gpd
import matplotlib.pyplot as plt
import fiona; fiona.supported_drivers

from RSSModelV4_Feb2021 import RSSModel


import time


'''----------------------------------------------------------------------------
Set up the interface window
----------------------------------------------------------------------------'''

root = tk.Tk(className = " RSS Model V4, NIWA 2021")


titleLabel = tk.Label(root, text="Road Stormwater Screening  Model V. 4: Settings", fg = "blue", \
font =("Ariel", 12))
titleLabel.grid(row=0, column=0, columnspan = 6, sticky = (tk.W))

root.tk.call('wm', 'iconphoto', root._w, tk.PhotoImage(file="InputData/NIWA_small.gif"))

'''----------------------------------------------------------------------------
#Make widget functions
---------------------------------------------------------------------------'''

#Labels
def MakeLabel (textString, rowNum, colNum, span, sticky):
    labelName = tk.Label(root, text = textString, font =("Ariel", 10))
    labelName.grid(row = rowNum, column = colNum, columnspan = span, sticky = sticky, \
    padx = 10, pady = 10)
    return labelName
    
    
#Buttons

'''----------------------------------------------------------------------------
Add runName
----------------------------------------------------------------------------'''
rowCount = 1

MakeLabel("Scenario name", rowCount, 0, 2, (tk.W))

rowCount += 1

text = tk.StringVar(root, value = "EnterName")

scenarioEntry = tk.Entry(root, textvariable = text, justify = "l")
scenarioEntry.grid(row = rowCount, column = 0, columnspan = 4, padx = 10, pady = 10, \
sticky = (tk.W, tk.E, tk.N))
    
rowCount += 1

"""----------------------------------------------------------------------------
Add parameter choice for default level of  treatment
---------------------------------------------------------------------------"""

#Make selection list

globalList = ["Default", "User defined"]


MakeLabel("Global parameters:", rowCount, 0, 1, (tk.W))



globalVariable = tk.StringVar(root) 

counter = 0

for parameter in globalList: 
    globalRadio = tk.Radiobutton(root, text = parameter, variable = globalVariable, value = parameter)
    globalRadio.grid(row = rowCount , column = 1 + counter,  columnspan = 1, padx = 10, pady = 10, sticky = (tk.W))
    counter += 1
    
globalVariable.set("Default")  
    
rowCount += 1
    
MakeLabel("Apply customised treatment files:", rowCount, 0, 1, (tk.W))

rowCount += 1

roadLRFVariable = tk.IntVar(root) 

roadLRFCheck = tk.Checkbutton(root, variable = roadLRFVariable, onvalue = 1, offvalue = 0, \
            text = "Road runoff")
    
roadLRFCheck.grid(row = rowCount, column = 0,  columnspan = 1, padx = 10, pady = 10, sticky = (tk.W))

roadLRFVariable.set(0) 

roadLRF = roadLRFVariable.get()

MakeLabel("Select road LRF file:", rowCount, 1, 1, (tk.W))

roadLRFVariable.set(0) # no customisation is default

#read in and list the road files

roadFileList = [" "]

for filename in os.listdir("CustomTreatment/"):
    if filename.startswith("Road") and filename != "RoadLRF_template.csv" :
        roadFileList.append(filename)   
        
roadMenu = ttk.Combobox(root, values = roadFileList, width = 40)
roadMenu.current(0) #PUTS the blank as the first choice
roadMenu.grid(row = rowCount,column = 2, columnspan = 3, padx = 10, pady = 10, sticky = (tk.W))

rowCount += 1


#read in and list the urban treatment files


urbLRFVariable = tk.IntVar(root) 

urbLRFCheck = tk.Checkbutton(root, variable = urbLRFVariable, onvalue = 1, offvalue = 0, \
            text = "Urban stormwater")
    
urbLRFCheck.grid(row = rowCount, column = 0,  columnspan = 1, padx = 10, pady = 10, sticky = (tk.W))

MakeLabel("Select stormwater LRF file:", rowCount, 1, 1, (tk.W))

urbLRFVariable.set(0)  # no customisation is default

urbFileList = [" "]

for filename in os.listdir("CustomTreatment/"):
    if filename.startswith("SW") and filename != "SWLRF_template.csv" :
        urbFileList.append(filename)   
        
urbMenu = ttk.Combobox(root, values = urbFileList, width = 40)
urbMenu.current(0)
urbMenu.grid(row = rowCount,column = 2, columnspan = 3, padx = 10, pady = 10, sticky = (tk.W))

rowCount += 1




"""----------------------------------------------------------------------------
Add color ramp
-----------------------------------------------------------------"""

MakeLabel("Select colour ramp:", rowCount, 0, 1, (tk.W))


rampList = ["Traffic light", "Colour blind safe"]


#Traffic No upstream sources = beige, Lowest = dark green, Lower = light green
#medium = yellow, higher = orange, highest = red - Colours are in HEX format
# https://www.color-hex.com/ e5e5ff

traffic = ["#fde7d6", "#66b266", "#9acd32", "#ffff66", "#ffb732", "#ff4d4d"]
           
#colour blind pallette is from colorbrewer          
           
blind = ["#e5f5f9", "#fcc5c0", "#f768a1", "#dd3497", "#ae017e", "#7a0177"]

rampVariable = tk.StringVar(root) 

counter = 0

for ramp in rampList: 
    rampRadio = tk.Radiobutton(root, text = ramp, variable = rampVariable, value = ramp)
    rampRadio.grid(row = rowCount, column = 1 + counter,  columnspan = 1, padx = 10, pady = 10, sticky = (tk.W))
    counter += 1


    
rampVariable.set("Traffic light")   

rowCount += 1


"""---------------------------------------------------------------------------
Make shapefiles and jpegs
-----------------------------------------------------------------------------"""

shpVariable = tk.IntVar(root) 

#counter = 0

# for shp in shpList: 
#     shpRadio = tk.Radiobutton(root, text = shp, variable = shpVariable, value = shp)
#     shpRadio.grid(row = 4 + counter, column = 2,  columnspan = 1, padx = 10, pady = 10, sticky = (tk.W))
#     counter += 1

shpCheck = tk.Checkbutton(root, variable = shpVariable, onvalue = 1, offvalue = 0, \
            text = "Make shapefile")
    
shpCheck.grid(row = rowCount, column = 0,  columnspan = 1, padx = 10, pady = 10, sticky = (tk.W, tk.N))
#     counter += 1

   
shpVariable.set(1)  

jpgVariable = tk.IntVar(root) 

jpgCheck = tk.Checkbutton(root, variable = jpgVariable, onvalue = 1, offvalue = 0, \
            text = "Make map images")
    
jpgCheck.grid(row = rowCount, column = 1,  columnspan = 1, padx = 10, pady = 10, sticky = (tk.W, tk.N))
#     counter += 1

   
jpgVariable.set(1)  

rowCount += 1
   
   
"""----------------------------------------------------------------------------
Add logos
----------------------------------------------------------------------------"""

img1 = tk.PhotoImage(file = "InputData/NIWA_small.gif")
imageLabel1 = tk.Label(root, image = img1)
imageLabel1.grid(row = rowCount, column = 3, rowspan = 2, columnspan = 1,  padx = 10, pady = 10, sticky = (tk.W))

img2 = tk.PhotoImage(file = "InputData/NZTA.gif")
imageLabel2 = tk.Label(root, image = img2)
imageLabel2.grid(row = rowCount, column = 1, columnspan = 2, rowspan = 2, padx = 10, pady = 10, sticky = (tk.W, tk.N))


'''----------------------------------------------------------------------------
Get the input data from the widgets
----------------------------------------------------------------------------'''

def GetEntries():
    
    
    #Get the scenario name
    runName = str(scenarioEntry.get())
    
    
    print ("Run name:", runName)
    
    outputPath = "Outputs/" + runName + "/"
           
    
    #Get the selected criteria from the list boxes       
    
    globalParameter = globalVariable.get()
            
    print ("Treatment parameter Choice: ", globalParameter)
    
    
    roadLRF = roadLRFVariable.get()
    
    roadCustom = roadMenu.get()
    
    if roadCustom == " ":
        roadCustom = "Templates/RoadLRF_template.csv"
    
    if roadLRF == 1:
        print ("Using customised road treatment", roadCustom)
    else:
        print ("Not using customised road treatment", roadCustom)
   
    urbLRF = urbLRFVariable.get()
    
    urbCustom = urbMenu.get()    
    
    if urbCustom == " ":
        urbCustom = "Templates/SWLRF_templateFull.csv"
    
    if urbLRF == 1:
        print ("Using customised urban stormwater treatment", urbCustom)
    else:
        print ("Not using customised urban stormwater treatment", urbCustom)
    
    #Shapefiles?
    
    shape = shpVariable.get()
    
    if shape ==1:
        print ("Making shapefiles: Yes")
    else:
        print ("Making shapefiles: No") 
        
    #jpgs?        
        
    jpgimage = jpgVariable.get()
    
    if jpgimage ==1:
        print ("Making map images: Yes")
    else:
        print ("Making map images: No")  
    
    ramp = rampVariable.get()
    
    print ("Colour ramp: ", ramp)
    
    
    def RunModel():   
    
        if ramp == "Traffic light":
                      
            endMessage = RSSModel(runName, outputPath, globalParameter, roadLRF, roadCustom, \
                                  urbLRF, urbCustom, shape, jpgimage, traffic,  "black")
                   
        
        else:
            endMessage = RSSModel(runName, outputPath, globalParameter, roadLRF, roadCustom, \
                                  urbLRF, urbCustom, shape, jpgimage, traffic, "white")
            
        return endMessage
    
   
 
    if os.path.isdir(outputPath):
        pathResult = messagebox.askquestion("Run already exists!", "WARNING, existing files will be overwritten. \n Continue?", \
                                            icon = "warning")
        
        if pathResult == "yes": #carry on
            endMessage = RunModel()
            
            if endMessage != "Ready to make a new scenario":
                messagebox.showerror("Setup error", endMessage)
         
            else:
                messagebox.showinfo("Scenario Complete", endMessage)
            
        else:
            print ("Type in a new run name")
                
    else:
        os.makedirs(outputPath)
        endMessage =  RunModel()
        
        if endMessage != "Ready to make a new scenario":
            messagebox.showerror("Setup error", endMessage)
     
        else:
            messagebox.showinfo("Scenario Complete", endMessage)
                       
     
'''----------------------------------------------------------------------------
Add the run button
----------------------------------------------------------------------------'''

runButton = tk.Button(root, text = "Run", command = GetEntries, padx = 10, \
fg = "blue", bg= "pink", font =("Ariel", 25))
runButton.grid(row = rowCount, column = 0, columnspan = 1, padx=15, pady= 15, sticky = (tk.W, tk.N))  


#root.columnconfigure(0, minsize = 100, pad = 20)
root.columnconfigure(1, minsize = 100, pad = 20)

root.mainloop()

#------------------------------------------------------------------------------




   

