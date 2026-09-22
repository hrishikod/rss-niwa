# -*- coding: utf-8 -*-
"""
Created on Thu Apr  2 14:54:10 2020

@author: daviesaf

RSS National Model for NZTA 

Created in Project NTA20102 

Units

lengths = m
witdth = m

areas = sq.m

flow = cummecs (m3/s)

loads = g / y

concentrations = g / m3
"""


"""-----------------------------------------------------------------------------
#Import libraries
----------------------------------------------------------------------------"""
    
import os

import numpy as np
import pandas as pd
import xlsxwriter
import geopandas as gpd
import matplotlib.pyplot as plt
import fiona; fiona.supported_drivers

import time
    
def RSSModel (runName, outputPath, globalParameter, roadLRF, roadCustom, \
            urbLRF, urbCustom, shape, jpgimage, colourList, fontColour): 
            
    
    """-----------------------------------------------------------------------------
    Dictionary function using csv files and Pandas
    ----------------------------------------------------------------------------"""
         
    def MakeDict (DF, colIndex, colValue):
    
        DF = DF.set_index(colIndex)
    
        Dict = {}
    
        rowCounter = 0
            
        for row in DF.itertuples():
            rowID = DF.index[rowCounter]
            Dict[rowID] = DF.loc[rowID, colValue]
        
            rowCounter += 1 
        
        return Dict
    
    
    """----------------------------------------------------------------------------
    Divider to handle zero denonimators
    --------------------------------------------------------------------------"""
    def Divider (numerator, denominator, arrayLength): 
        
        out = np.zeros(arrayLength).astype(float)
        np.divide(numerator, denominator, out = out, where=denominator != 0 )
        
        return out   

    """--------------------------------------------------------------------------
    Validation of model settings
    ----------------------------------------------------------------------------"""
    
    codeTime = time.time()
    
    print ("Validating settings")   
    #return an error message and do not do modelling for following conditions
    
    print ("urbLRF: ",  urbLRF)
    print ("urbcustom: " ,  urbCustom)
    
    print ("roadLRF: ",  roadLRF)
    print ("roadcustom: " ,  roadCustom)
    
    if roadLRF == 0 and roadCustom != "Templates/RoadLRF_template.csv":
        endMessage = "Information missmatch: Road runoff customisation is not checked but a road LRF file is selected"
        
    elif urbLRF == 0 and urbCustom != "Templates/SWLRF_templateFull.csv":
        endMessage = "Information missmatch: Stormwater customisation is not checked but a stormwater LRF file is selected"
        
    elif roadLRF == 1 and roadCustom == "RoadLRF_template.csv":
        endMessage = "Information missmatch: Road runoff customisation is checked but no road LRF file is selected"
    
    elif urbLRF == 1 and urbCustom == "SWLRF_templateFull.csv":
        endMessage = "Information missmatch: Stormwater customisation is checked but no stormwater LRF file is selected"
    
    else: #otherwise do the modelling
    
        print ("Starting Run")
        
        
        """----------------------------------------------------------------------------
        Read in and make parameters
        
        required xlrd to be installed in Python
        ----------------------------------------------------------------------------"""
        print ("Making parameters")
        
        path = "Parameters/"
        
        # parameters where users can choose their own values
        
        
        def Param (df,param):
            parameter = df.loc[param][globalParameter]
            return parameter
        
        #Road Parameters
        
        roadPdf = pd.read_excel(path + "ModelParameters.xlsx", sheet_name = "RoadParameters")
        roadPdf = roadPdf.set_index("Name")
        
        Catchpit = Param (roadPdf,"Catchpit") #Load reduction fraction (catchpits)
        InfilGood = Param (roadPdf,"InfilGood") #Load reduction fraction (infiltration, good drainage)
        InfilPoor = Param (roadPdf,"InfilPoor") # Load reduction fraction (infiltration, poor drainage)
        TWF0 = Param (roadPdf,"TWF0") # Trafficable Width Factor (0-3m lane width)
        TWF3 = Param (roadPdf,"TWF3") # Trafficable Width Factor (3-4m lane width)
        TWF4 = Param (roadPdf,"TWF4") # Trafficable Width Factor (4-5m lane width)
        TWF5 = Param (roadPdf,"TWF5") # Trafficable Width Factor (5-6m lane width)
        TWF6 = Param (roadPdf,"TWF6") # Trafficable Width Factor (6-7m lane width)
        TWF7 = Param (roadPdf,"TWF7") # Trafficable Width Factor (7-8m lane width)
        TWF8 = Param (roadPdf,"TWF8") # Trafficable Width Factor (>8m lane width)
        HvyFlat = Param (roadPdf,"HvyFlat") # Heavy vehicle car equivalent (flat terrain)
        HvyRolling = Param (roadPdf,"HvyRolling") # Heavy vehicle car equivalent (rolling terrain)
        HvySteep = Param (roadPdf,"HvySteep")# Heavy vehicle car equivalent (steep terrain)
        CapFac = Param (roadPdf,"CapFac") # Traffic capacity factor assuming 2 lanes
        DD = Param (roadPdf,"DD") # DD (50/50 split)
        ZnVEF1 = Param (roadPdf,"ZnVEF1") # Zn Vehicle Emission Factor (LOS 1, free-flow)
        ZnVEF2 = Param (roadPdf,"ZnVEF2") # Zn Vehicle Emission Factor (LOS 2, interupted)
        ZnVEF3 = Param (roadPdf,"ZnVEF3") # Zn Vehicle Emission Factor (LOS 3, congested)
        CuVEF1 = Param (roadPdf,"CuVEF1") # Cu Vehicle Emission Factor (LOS 1, free-flow)
        CuVEF2 = Param (roadPdf,"CuVEF2") # Cu Vehicle Emission Factor (LOS 2, interupted)
        CuVEF3 = Param (roadPdf,"CuVEF3") # Cu Vehicle Emission Factor (LOS 3, congested)
        
        
        #Urban parameters
        
        urbanPdf = pd.read_excel(path + "ModelParameters.xlsx", sheet_name = "UrbanParameters")
        urbanPdf = urbanPdf.set_index("Name")
        
        ZnYieldRes = Param (urbanPdf,"ZnYieldRes") # Zn yield g/m2/y (residential)
        ZnYieldResSC = Param (urbanPdf,"ZnYieldResSC") # Zn yield g/m2/y (residential) with SC
        ZnYieldIC = Param (urbanPdf,"ZnYieldIC") # Zn yield g/m2/y (industrial/commercial)
        ZnYieldICSC = Param (urbanPdf,"ZnYieldICSC") # Zn yield g/m2/y (industrial/commercial) with SC
        CuYieldRes = Param (urbanPdf,"CuYieldRes") # Cu yield g/m2/y (residential)
        CuYieldResSC = Param (urbanPdf,"CuYieldResSC") # Cu yield g/m2/y (residential) with SC
        CuYieldIC = Param (urbanPdf,"CuYieldIC") # Cu yield g/m2/y (industrial/commercial)
        CuYieldICSC = Param (urbanPdf,"CuYieldICSC") # Cu yield g/m2/y (industrial/commercial) with SC
        ZnLRFResP = Param (urbanPdf,"ZnLRFRes") # Zn Load reduction fraction (residential)
        ZnLRFICP = Param (urbanPdf,"ZnLRFIC") # Zn Load reduction fraction (industrial/commercial)
        CuLRFResP = Param (urbanPdf,"CuLRFRes") # Cu Load reduction fraction (residential)
        CuLRFICP = Param (urbanPdf,"CuLRFIC") # Cu Load reduction fraction (industrial/commercial)
        ImpResFrac = Param (urbanPdf,"ImpRES") # Fraction imperviousness (residential)
        ImpICFrac = Param (urbanPdf,"ImpIC") # Fraction imperviousness (industrial/commercial)
        
        #Parameters where there is no treatment choice for users
        
        globalParameter = "Default"
        
        #Streams
        
        streamPdf = pd.read_excel(path + "ModelParameters.xlsx", sheet_name = "StreamParameters")
        streamPdf = streamPdf.set_index("Name")
        
        CuANZECC = Param (streamPdf,"CuANZECC") # Cumulative Criterion Unit Parameters (ANZECC 99% Zn concentration)
        ZnANZECC  = Param (streamPdf,"ZnANZECC") # Cumulative Criterion Unit Parameters (ANZECC 99% Cu concentration)
        StreamLowerCCU  = Param (streamPdf,"StreamLowerCCU") # Cumulative Criterion Unit Parameters (Lower threshold)
        StreamUpperCCU  = Param (streamPdf,"StreamUpperCCU") # Cumulative Criterion Unit Parameters (Upper threshold)
        Substrate  = Param (streamPdf,"Substrate") # MCI (Stream substrate soft/hard threshold)
        HardEx  = Param (streamPdf,"HardEx") # MCI (Hard bottom - Excellent)
        HardPF  = Param (streamPdf,"HardPF") # MCI (Hard bottom - Poor/Fair)
        SoftEx  = Param (streamPdf,"SoftEx") # MCI (Soft bottom - Excellent)
        SoftPF  = Param (streamPdf,"SoftPF") # MCI (Soft bottom - Poor/Fair)
        
        #Coastal parameters NO user editing possible
        
        coastPdf = pd.read_excel(path + "ModelParameters.xlsx", sheet_name = "CoastalParameters")
        coastPdf = coastPdf.set_index("Name")
        
        ZnTEL = Param (coastPdf,"ZnTEL") # Cumulative Criterion Unit Parameters mg/kg (Zn TEL)
        CuTEL = Param (coastPdf,"CuTEL") # Cumulative Criterion Unit Parameters mg/kg (Cu TEL)
        CoastLowerCCU = Param (coastPdf,"CoastLowerCCU") # Cumulative Criterion Unit Parameters (Lower threshold)
        CoastUpperCCU = Param (coastPdf,"CoastUpperCCU") # Cumulative Criterion Unit Parameters (Upper threshold)
        TrapHigh = Param (coastPdf,"TrapHigh") #Upper threshold trap efficiency
        TrapLow = Param (coastPdf,"TrapLow") #Lower threshold trap efficiency
        
        del  urbanPdf, roadPdf, coastPdf, streamPdf
              
        
        """-----------------------------------------------------------------------------
        Read in the REC 2.4 stream and catchment data and make dictionaries
        ----------------------------------------------------------------------------"""
        
        print ("Reading in REC 2.4 data")
        
        #catchDF = pd.read_csv("InputData/CatchmentDataREC2_4_Henderson3.csv", encoding = "Latin1")
        catchDF = pd.read_csv("InputData/CatchmentDataREC2_4.csv", encoding = "Latin1")
        
        #make sure the DF is sorted by HydroSeq
        
        catchDF = catchDF.sort_values(by = ["Hydseq"])
        
        #Calculate the number of reaches to be modelled.  This will be used throughout
        #to create new arrays with the correct number of rows
        
        lenCatch = len(catchDF) 
        
        # area in sq,m
        
        catchArea = catchDF["CATAREA"].values
            
        # From and To nodes (make a dictionary of the nodes for routing)
        
        fromNode = catchDF["FNODE"].values
        
        toNode = catchDF["TNODE"].values
        
        nodeDict = {}
        
        #make an array of nodes to add to the dictionary
        
        nodeArray = np.append(toNode, fromNode)
        
        #cycle through the node array and add a blank entry for each node,
        
        for node in nodeArray:
            
            #first check if the node already exists
            
            try:
                value = nodeDict[node]
                
            #then add new node if it doesn't exist
                
            except KeyError:
                nodeDict[node] = 0
                
        
        
        
        #MCI comes from FENZ and is mapped to REC 2.4 from REC 1.  It was supplied by Richard Storey
        
        MCI = catchDF["MCI"].values
        
        #Urban and rural fractions were obtained in GIS by interesecting the REC subcatchments
        #with LCDB4 and then doing a pivot table in Excel
        
        fracUrbBuilt = catchDF["FracUrbBuilt"].values
        # fracUrbGreen = catchDF["FracUrbGreen"].values
        # fracRural = catchDF["FracRural"].values 
        
        fracBuiltRes = catchDF["fracBuiltRes"].values
        fracBuiltIC = catchDF["fracBuiltIC"].values
        
        #baseSub is the hardness of bed sediments and comes from FENZ (ReachSed in River predictors)
        
        baseSub	=  catchDF["BaseSub"].values
        
        #slope comes from a zonal statistic table with slopes classed
        # using LRI classes by REC2 reach and is the dominant class in the subcatchment.  
        #The model slope classes are stored as a dictionary for use in the road calcs:
        # 1 = Flat (<=7 degrees)
        # 2 = Rolling (7-20 degrees)
        # 3 = Steep / mountainous (>20 degrees)
        
        slopeDict = MakeDict (catchDF, "nzsegment", "RSSslopeClass")
            
        #Drainage class is the dominant FSL drainage class for a reach determined using GIS zonal stats
        # 5 = excellent drainage and 1 is poor
        #the model drainage classes are  1=poor (1 to 3 in FSL) and 2 = excellent (4-5 in FSL)
        #The model drainages classes are stored as a dictionary for use in the road calcs:
        
        drainDict = MakeDict (catchDF, "nzsegment", "RSSdrainClass")
        
        #Mean Q has been mapped from CLUES (Woods et al 2006), volume is annual
        
        meanQ =  catchDF["MeanQ"].values
        
        volume = meanQ *(60*60*24*365)
        
                
        """----------------------------------------------------------------------------
        Make output and estuary DF
        ------------------------------------------------------------------------------"""   
        
        colList =["nzsegment", "CATAREA", "Hydseq", "FNODE", "TNODE", "Region", "cumSedLoad", "StreamLength_km",	\
                  "Terminal", "Estuary", "EstTrapEff"]
        
        outputDF = catchDF[colList].copy(deep = True)
        outputDF = outputDF.set_index("nzsegment")
        
        # estuaryDF = pd.read_csv("InputData/OutputTemplate.csv", encoding = "Latin1")
        # estuaryDF = estuaryDF.set_index("nzsegment")
        
        estuaryDF = outputDF.copy(deep = True)
        
        #Drop non coastal reaches
        
        estuaryDF = estuaryDF[(estuaryDF.Estuary != "Inland")]
        
        # drop all the columns not needed for estuaries
        
        colDropList = ['CATAREA', 'Hydseq', 'FNODE', 'TNODE', 'Terminal', ]
        
        estuaryDF = estuaryDF.drop(columns = colDropList)
        
        #set the output folder
        
        outputPath = "Outputs/" + runName + "/"
        
               
        if not os.path.isdir(outputPath):
                os.makedirs(outputPath) 
        
        """-----------------------------------------------------------------------
        Read in and add the custom SW LRFs to the catchment DF
        ----------------------------------------------------------------------"""
        
        SWLRFdf = pd.read_csv("CustomTreatment/" + urbCustom, encoding = "Latin1")

        # Some older/custom SW LRF files do not include the optional Source Control column.
        # Default it to 0 so the model still runs rather than crashing.
        if "Source Control" not in SWLRFdf.columns:
            SWLRFdf["Source Control"] = 0

        SWheadDict ={"LRF Zn Residential": "ZnLRFRes", "LRF Zn Commercial and Industrial": "ZnLRFIC", \
                      "LRF Cu Residential": "CuLRFRes", "LRF Cu Commercial and Industrial": "CuLRFIC", \
                    "Source Control": "sControl"}


        catchDF = catchDF.merge(SWLRFdf[["nzsegment","LRF Zn Residential", "LRF Zn Commercial and Industrial",\
                "LRF Cu Residential", "LRF Cu Commercial and Industrial", "Source Control"]], on = "nzsegment", how="left")
            
        catchDF = catchDF.rename(columns = SWheadDict)
        
        #Replace NANs with 0 in non urban subcatchments
        
        
        
        #put in the parameter values where thre are no custom values
        
        catchDF = catchDF.replace({"ZnLRFRes": 0},ZnLRFResP)
        
        catchDF = catchDF.replace({"ZnLRFIC": 0},ZnLRFICP)
        
        catchDF = catchDF.replace({"CuLRFRes": 0},CuLRFResP)
        
        catchDF = catchDF.replace({"CuLRFIC": 0},CuLRFICP) 
        
        
        #make into arrays for calculation
        
        ZnLRFRes = catchDF["ZnLRFRes"].values
        
        ZnLRFIC = catchDF["ZnLRFIC"].values
        
        CuLRFRes = catchDF["CuLRFRes"].values
        
        CuLRFIC = catchDF["CuLRFIC"].values
        
        sControl=catchDF["sControl"].values
        
        #make yield arrays for 
        
        
        # #make csv to test
        
        # catchDF.to_csv("Catch test.csv")
        
        """-----------------------------------------------------------------------------
        Read in the RAMM road data
        The RSS data is suppled by section of Road direct from the RAMM data sets
        The segments by REC reach and land use are supplied with the segment length.
        The two are linked by the unique ID created in GIS (Concat_ID)
        
        I first make data frames and then NUMPY arrays for the segments for calculations
        ----------------------------------------------------------------------------"""
        
        print ("Reading in RAMM data")
        
        # RAMMdataDF = pd.read_csv("InputData/RAMMData.csv", encoding = "Latin1")
        # RAMMdataDF = RAMMdataDF.set_index("Concat_ID")
        
        RAMMsegmentDF = pd.read_csv("InputData/RAMMsegments.csv", encoding = "Latin1")
        RAMMsegmentDF = RAMMsegmentDF.set_index("Concat_ID")
        
        #add the RAMM data to the segment df.  Since both have the same index, it will 
        #do it automatically like a VLOOKUP.  Left means that only the roads that are in 
        #the segment DF are included
        
        #RAMMsegmentDF = RAMMsegmentDF.join(RAMMdataDF, how = "left")
        
        #add the slope and drain based on the NZ segment from their respective dictionaries
        
        RAMMsegmentDF["SlopeClass"] = RAMMsegmentDF["nzsegment"].map(slopeDict)
        
        RAMMsegmentDF["DrainClass"] = RAMMsegmentDF["nzsegment"].map(drainDict)
        
        #Make arrays for calculations
        
        segLU = RAMMsegmentDF["UrbanCode"].values # 1 = built-up, 2 = green, 0 = rural
        
        #get array length
        
        RAMMarrayLength = len(segLU)
        
        #make arrays of the data
        
        segLen = RAMMsegmentDF["Length"].values
        
        addt = RAMMsegmentDF["AADT_VPD"].values
        
        hvyFrac = RAMMsegmentDF["HvyFrac"].values
         
        width = RAMMsegmentDF["Width"].values
        
        slope = RAMMsegmentDF["SlopeClass"].values #1 flat, 2=rolling, 3 = steep
         
        drain = RAMMsegmentDF["DrainClass"].values # 1= poor, 2 = good
        
        SH = RAMMsegmentDF["SH"].values # 0 = local, 1 = state highway
        
        
        roadArea = width * segLen
        
        """-------------------------------------------------------------------------
        Read in custom road LRFs
        Note, the catchpit and infiltraton are applied later on to instances were 
        there is no custom value (i.e., LRF = 0)
        ---------------------------------------------------------------------------"""
        
        roadLRFdf = pd.read_csv("CustomTreatment/" + roadCustom, encoding = "Latin1")
                
        roadHeadDict ={"LRF for Zn from SH": "ZnLRFSH", "LRF for Zn from local": "ZnLRFloc", \
                      "LRF for Cu from SH": "CuLRFSH", "LRF for Cu from local": "CuLRFloc"}


        RAMMsegmentDF = RAMMsegmentDF.merge(roadLRFdf[["MergeID","LRF for Zn from SH", "LRF for Zn from local",\
                "LRF for Cu from SH", "LRF for Cu from local"]], on = "MergeID", how="left")
            
        RAMMsegmentDF = RAMMsegmentDF.rename(columns = roadHeadDict)
         
        
        #make into arrays for calculation
        
        ZnLRFSH = RAMMsegmentDF["ZnLRFSH"].values
        
        ZnLRFloc = RAMMsegmentDF["ZnLRFloc"].values
        
        CuLRFSH = RAMMsegmentDF["CuLRFSH"].values
        
        CuLRFloc = RAMMsegmentDF["CuLRFloc"].values
        
         
        #replace with parameter values where no value
        
        #removal factors from load reduction factors, catchpits if urban and infiltration if rural
        #assumes same reduction for both metals
        
        def LRFreplace (LRF):
        
            LRF = np.where((segLU == 1) & (LRF == 0), Catchpit, LRF)
            
            LRF = np.where((segLU ==2) & (LRF == 0), Catchpit, LRF)
            
            LRF = np.where((segLU == 0) & (drain ==2) & (LRF == 0), InfilGood, LRF)
        
            LRF = np.where((segLU == 0) & (drain ==1) & (LRF == 0), InfilPoor, LRF)
        
            return LRF
        
        ZnLRFSH = LRFreplace(ZnLRFSH) 
        
        ZnLRFloc = LRFreplace(ZnLRFloc)
        
        CuLRFSH = LRFreplace(CuLRFSH)
        
        CuLRFloc = LRFreplace(CuLRFloc)
        
        #Make a single Zn and Cu LRF array to make later calcs easier
        
        ZnLRFroad = ZnLRFSH * SH + ZnLRFloc * (1 - SH)
        
        CuLRFroad = CuLRFSH * SH + CuLRFloc * (1 - SH)    
        
        # # testing
        
        # RAMMsegmentDF["ZnLRFSH2"] = ZnLRFSH.tolist()
        
        # RAMMsegmentDF["ZnLRFloc2"] = ZnLRFloc.tolist()
         
        # RAMMsegmentDF["CuLRFSH2"] = CuLRFSH.tolist()
          
        # RAMMsegmentDF["CuLRFloc2"] = CuLRFloc.tolist()
        
        # RAMMsegmentDF["ZnLRFroad"] = ZnLRFroad.tolist()
        # RAMMsegmentDF["CuLRFroad"] = CuLRFroad.tolist()
                
        
        """------------------------------------------------------------------------------
        Calculate Road Contaminants
        -----------------------------------------------------------------------------"""
        print ("Calculating contaminants from roads")
        
        #estimating road capacity and Level of Service
        
        roadArea = width * segLen
        
        roadAreaUrb = np.zeros(RAMMarrayLength).astype(float)
        
        np.copyto(roadAreaUrb, roadArea, where = ((segLU == 1) | (segLU ==2)))
        
        #trafficable width (road + shoulder)
        
        trafWidth = np.zeros(RAMMarrayLength).astype(float) 
        
        np.copyto(trafWidth, width + TWF0, where = (width <= 3 )) 
        
        np.copyto(trafWidth, width + TWF3, where = ((width > 3) | (width <= 4)))
        
        np.copyto(trafWidth, width + TWF4, where = ((width > 4) | (width <= 5)))
        
        np.copyto(trafWidth, width + TWF5, where = ((width > 5) | (width <= 6)))
        
        np.copyto(trafWidth, width + TWF6, where = ((width > 6) | (width <= 7)))
        
        np.copyto(trafWidth, width + TWF7, where = ((width > 7) | (width <= 8)))
        
        np.copyto(trafWidth, width + TWF8, where = (width > 6))
        
        #Truck factor (= 1 where no trucks)
        
        truckFactor = np.ones(RAMMarrayLength).astype(float) 
        
        np.copyto(truckFactor, 1/(1 + hvyFrac*(HvyFlat - 1)), where = (slope == 1)) 
        np.copyto(truckFactor, 1/(1 + hvyFrac*(HvyRolling - 1)), where = (slope == 2))
        np.copyto(truckFactor, 1/(1 + hvyFrac*(HvySteep - 1)), where = (slope == 3))
        
        #Capacity is funciton of vpd 
        
        capacity = CapFac  * DD * trafWidth * truckFactor * 10
        
        
        
        
        #level of service
        los = Divider (addt, capacity, len(capacity))
        
        losClass = np.ones(RAMMarrayLength).astype(np.int8)
        losClass [los >= 0.7] = 3
        losClass [los < 0.7] = 2
        losClass [los < 0.35] = 1
        
        #Vehicle emission factors (depending on LOS)
        
        znVEF = np.ones(RAMMarrayLength).astype(float)
        
        znVEF[losClass == 1] = ZnVEF1
        znVEF[losClass == 2] = ZnVEF2
        znVEF[losClass == 3] = ZnVEF3
        
        cuVEF = np.ones(RAMMarrayLength).astype(float)
        
        cuVEF[losClass == 1] = CuVEF1
        cuVEF[losClass == 2] = CuVEF2
        cuVEF[losClass == 3] = CuVEF3
        
        
        #Daily vehicle kilometers travelled veh_km/day
        
        vkt = (addt * segLen)/1000
        
        
        #Calculate the metal loads per year in g / year 
        
        roadZn = (1-ZnLRFroad) * znVEF * vkt * 365 / 1000 
        
        roadCu = (1-CuLRFroad) * cuVEF * vkt * 365 / 1000
        
                
        #add loads to dataframe and do pivot for segments and State Highways
        
        RAMMsegmentDF["roadZn"] = roadZn.tolist()
        RAMMsegmentDF["roadCu"] = roadCu.tolist()
        RAMMsegmentDF["roadArea"] = roadArea.tolist()
        RAMMsegmentDF["roadAreaUrb"] = roadAreaUrb.tolist()
        
        # #make csv to test
        
        # RAMMsegmentDF.to_csv(outputPath +"Road test.csv")
        
        
        #remove Concat ID as an index before pivot
        
        RAMMsegmentDF.reset_index()
        
        #segmentPivot = pd.pivot_table(RAMMsegmentDF, index = ["nzsegment", "SH"], values = ["roadArea", "roadZn", "roadCu", ], aggfunc = sum)
        
        #using groupby instead of pivot preserves the order, pivot resorts alphabetically.
        segmentPivot = RAMMsegmentDF.groupby(["nzsegment", "SH"])[["roadArea", "roadAreaUrb", "roadZn", "roadCu"]].sum()
        
        segmentPivot = segmentPivot.reset_index()
        segmentPivot = segmentPivot.set_index("nzsegment")
        
        
        #split into state highway and local road loads
        
        localSegment = segmentPivot[segmentPivot.SH == 0]
        localSegment = localSegment.drop(columns=["SH"])
        
        
        stateSegment = segmentPivot[segmentPivot.SH == 1]
        stateSegment = stateSegment.drop(columns=["SH"])
        
        #add as generated loads to the output dataframe
        
        outputDF = outputDF.join(localSegment)
        
        outputDF = outputDF.rename(columns = {"roadZn" : "genRoadZnLocal",\
            "roadCu" : "genRoadCuLocal", "roadArea" : "areaRoadLocal", "roadAreaUrb" : "areaRoadUrbLocal"})
        
        outputDF = outputDF.join(stateSegment)
        
        outputDF = outputDF.rename(columns = {"roadZn" : "genRoadZnSH", \
                "roadCu" : "genRoadCuSH", "roadArea" : "areaRoadSH", "roadAreaUrb" : "areaRoadUrbSH"})
            
        outputDF = outputDF.fillna(0) #assign a zero to all reaxhes with no roads
        
        #Grab the outputs as arrays for modelling(use old names, new are aliases)
        
        genRoadZnLocal = outputDF["genRoadZnLocal"].values 
        genRoadZnSH = outputDF["genRoadZnSH"].values
        
        genRoadCuLocal = outputDF["genRoadCuLocal"].values 
        genRoadCuSH = outputDF["genRoadCuSH"].values
        
        roadAreaLocal = outputDF["areaRoadLocal"].values 
        roadAreaSH = outputDF["areaRoadSH"].values
        roadAreaTot = roadAreaLocal + roadAreaSH
        roadAreaUrb = outputDF["areaRoadUrbLocal"].values + outputDF["areaRoadUrbSH"].values
           
        
        """-----------------------------------------------------------------------------
        Calculate the urban contaminant loads
        -----------------------------------------------------------------------------"""
        
        print ("Calculating generated loads from urban areas")
        
        #calculate urban areas less roads    
        
        builtArea = catchArea * fracUrbBuilt - roadAreaUrb
        
        builtArea[builtArea < 0] = 0
        
        resArea = fracBuiltRes * builtArea
        
        indComArea = fracBuiltIC * builtArea
        
        resImpArea = resArea * ImpResFrac 
        
        indComImpArea = indComArea * ImpICFrac
        
        #Calculate the loads (no metals from green space or permeable)
        
        #Make yield arrays for source and non source control    
        
        znYeildResArray = np.ones(lenCatch).astype(float)
        
        znYeildResArray[sControl == 0] = ZnYieldRes
        znYeildResArray[sControl == 1] = ZnYieldResSC
        
        znYeildICArray = np.ones(lenCatch).astype(float)
        
        znYeildICArray[sControl == 0] = ZnYieldIC
        znYeildICArray[sControl == 1] = ZnYieldICSC
        
        cuYeildResArray = np.ones(lenCatch).astype(float)
        
        cuYeildResArray[sControl == 0] = CuYieldRes
        cuYeildResArray[sControl == 1] = CuYieldResSC
        
        cuYeildICArray = np.ones(lenCatch).astype(float)
        
        cuYeildICArray[sControl == 0] = CuYieldIC
        cuYeildICArray[sControl == 1] = CuYieldICSC
        
        
        #do the load calcs       
        
        
        genZnRes = resImpArea * znYeildResArray *(1 - ZnLRFRes)
        genZnIC = indComImpArea * znYeildICArray *(1 - ZnLRFIC)
        
        genUrbZn = genZnRes + genZnIC
        
        genCuRes = resImpArea * cuYeildResArray *(1 - CuLRFRes)
        genCuIC = indComImpArea * cuYeildICArray *(1 - CuLRFIC)
        
        genUrbCu = genCuRes + genCuIC
        
        #add to the output file
        
        outputDF["ZnYield test"] = znYeildResArray.tolist()
        
        outputDF["genUrbZn"] = genUrbZn.tolist()
        
        outputDF["genUrbCu"] = genUrbCu.tolist()
        
        outputDF["BuiltArea"] = builtArea.tolist()
        
        outputDF["resImpArea"] = resImpArea.tolist()
        
        outputDF["ICImpArea"] = indComImpArea.tolist()  
        
        
        #  #make csv to test
        
        # outputDF.to_csv("urb test.csv")
        
                
        """-----------------------------------------------------------------------------
        Routing functions and calculations
        Note, no attenuation
        ------------------------------------------------------------------------------"""
        print ("Routing contaminants")
        
        def RoutingLoads(conArray, contaminantName): 
            
            print (contaminantName)
            
            #make dictionaries to hold the loads in the calcs
                   
            routeNodeDict = nodeDict.fromkeys(nodeDict, 0)
            
            #make  empty arraya to add the reach loads to
            reachLoad = np.zeros(lenCatch).astype(float)  
                
            for reach in range(lenCatch):
                           
                #get load from upstream reaches,.  NOte, headwaters will have 
                #an entry of zero.  
                
                upstreamLoad = (routeNodeDict[fromNode[reach]])
                
                reachLoad[reach] = upstreamLoad + conArray[reach]
                
                #add the reach node to the NodeDict entry for the reach to Node and to the
                #reachLoad array
                
                routeNodeDict[toNode[reach]] += (reachLoad[reach])
                
            reachConc = reachLoad / volume
            
                
            outputDF["cumLoad" + contaminantName] = reachLoad.tolist()
            outputDF["conc" + contaminantName] = reachConc.tolist()
            
            return reachLoad, reachConc
        
        
        def RoutingAreas(areaArray, areaName): 
            
            #make dictionaries to hold the loads in the calcs
                   
            routeNodeDict = nodeDict.fromkeys(nodeDict, 0)
            
            #make  empty arraya to add the reach loads to
            reachArea = np.zeros(lenCatch).astype(float)  
                
            for reach in range(lenCatch):
                           
                #get area from upstream reaches,.  
                
                upstreamArea = (routeNodeDict[fromNode[reach]])
                
                reachArea[reach] = upstreamArea + areaArray[reach]
                
                #add the reach node to the NodeDict entry for the reach to Node and to the
                #reachLoad array
                
                routeNodeDict[toNode[reach]] += (reachArea[reach])
               
            outputDF["cumArea" + areaName] = reachArea.tolist()
            
            return reachArea
        
        #Local Roads
        
        cumRoadAreaLocal = RoutingAreas (roadAreaLocal, "RoadLocal")
        
        RoadZnLocal = RoutingLoads(genRoadZnLocal, "RoadZnLocal")
        cumRoadZnLocal = RoadZnLocal[0]
        concRoadZnLocal = RoadZnLocal[1]
                                     
        RoadCuLocal = RoutingLoads(genRoadCuLocal, "RoadCuLocal")
        cumRoadCuLocal = RoadCuLocal[0]
        concRoadCuLocal = RoadCuLocal[1]
        
        
        #State highways
        
        cumRoadAreaSH = RoutingAreas (roadAreaSH, "RoadSH")
        
        RoadZnSH = RoutingLoads(genRoadZnSH, "RoadZnSH")
        cumRoadZnSH = RoadZnSH[0]
        concRoadZnSH = RoadZnSH[1]
                                     
        RoadCuSH = RoutingLoads(genRoadCuSH, "RoadCuSH")
        cumRoadCuSH = RoadCuSH[0]
        concRoadCuSH = RoadCuSH[1]
        
        #All roads combined
    
        genRoadZnAll = genRoadZnLocal + genRoadZnSH
        outputDF["genRoadZnAll"] = genRoadZnAll.tolist()
        
        genRoadCuAll = genRoadCuLocal + genRoadCuSH
        outputDF["genRoadCuAll"] = genRoadCuAll.tolist()
        
        cumRoadAreaAll = cumRoadAreaLocal + cumRoadAreaSH
        outputDF["cumRoadAreaAll"] = cumRoadAreaAll.tolist()
        
        cumRoadZnAll = cumRoadZnLocal + cumRoadZnSH
        concRoadZnAll = cumRoadZnAll / volume
        outputDF["cumLoadRoadZnAll"] = cumRoadZnAll.tolist()
        outputDF["concRoadZnAll"] = concRoadZnAll.tolist()
        
        cumRoadCuAll = cumRoadCuLocal + cumRoadCuSH
        concRoadCuAll = cumRoadCuAll / volume
        outputDF["cumLoadRoadCuAll"] = cumRoadCuAll.tolist()
        outputDF["concRoadCuAll"] = concRoadCuAll.tolist()
        
        #Urban "built"
        
        cumUrbArea = RoutingAreas (builtArea, "Urb")
        
        UrbZn = RoutingLoads(genUrbZn, "UrbZn")
        cumUrbZn = UrbZn[0]
        concUrbZn = UrbZn[1]
        
        UrbCu = RoutingLoads(genUrbCu, "UrbCu")
        cumUrbCu = UrbCu[0]
        concUrbCu = UrbCu[1]
        
        #Comnined totals for roads and urban
        
        genZnLoadTot = genRoadZnLocal + genRoadZnSH + genUrbZn
        outputDF["genZnLoadTot"] = genZnLoadTot.tolist()
        
        genCuLoadTot = genRoadCuLocal + genRoadCuSH + genUrbCu
        outputDF["genCuLoadTot"] = genCuLoadTot.tolist()
        
        cumAreaTot = cumUrbArea + cumRoadAreaAll
        
        cumZnLoadTot = cumRoadZnLocal + cumRoadZnSH + cumUrbZn
        concZnTot = cumZnLoadTot / volume
        
        outputDF["cumZnLoadTot"] = cumZnLoadTot.tolist()
        outputDF["concZnTot"] = concZnTot.tolist()
        
        cumCuLoadTot = cumRoadCuLocal + cumRoadCuSH + cumUrbCu
        concCuTot = cumCuLoadTot / volume
        
        outputDF["cumAreaTot"] = cumAreaTot.tolist()
        outputDF["cumCuLoadTot"] = cumCuLoadTot.tolist()
        outputDF["concCuTot"] = concCuTot.tolist()
        
        
        """---------------------------------------------------------------------------
        Calculate stream risks
        ---------------------------------------------------------------------------"""
        
        print ("Calculating stream risks")
        
        #RES score is the same for both roads and urban and is based on the substrate hardness and MCI
        #bed sediments, hard = 1, soft = 0
        
        hardSoft = np.zeros(lenCatch).astype(float)  
        
        hardSoft[baseSub > Substrate] = 1
        hardSoft[baseSub <= Substrate] = 0
        
        RESscore = np.zeros(lenCatch).astype(np.int8)
        
        #hard beds
        
        np.copyto(RESscore, 3, where = ((hardSoft == 1) & (MCI >= HardEx)))
        
        np.copyto(RESscore, 2, where = ((hardSoft == 1) & (MCI < HardEx) & (MCI > HardPF)))
        
        np.copyto(RESscore, 1, where = ((hardSoft == 1) & (MCI <= HardPF)))
        
        #soft beds
        
        np.copyto(RESscore, 3, where = ((hardSoft == 0) & (MCI >= SoftEx)))
        
        np.copyto(RESscore, 2, where = ((hardSoft == 0) & (MCI < SoftEx) & (MCI > SoftPF)))
        
        np.copyto(RESscore, 1, where = ((hardSoft == 0) & (MCI <= SoftPF)))
        
        
        
        #Instream Concentration Cummulative Criterion Units (CCUs) and CS score
        #Method from Hickey and Golding 2002
        
        def CCUcalc (ZnConc, CuConc):
            CCU = ZnConc / ZnANZECC + CuConc / CuANZECC
            CCUscore = np.zeros(lenCatch).astype(np.int8)
            CCUscore[CCU >= StreamUpperCCU] = 5
            CCUscore[CCU < StreamUpperCCU] = 1
            CCUscore[CCU < StreamLowerCCU] = 0
            
            return CCUscore
        
        roadCCULocal = CCUcalc(concRoadZnLocal, concRoadCuLocal)
        roadCCUSH = CCUcalc(concRoadZnSH, concRoadCuSH)
        roadCCUAll = CCUcalc(concRoadZnAll, concRoadCuAll)
        urbanCCU = CCUcalc(concUrbZn, concUrbCu) 
        totalCCU = CCUcalc(concZnTot, concCuTot) 
        
        
        #Calculate the stream risk score
                          
        def StreamRisk (CCUscore, cumArea, riskName):
              risk = RESscore * CCUscore
              risk[cumArea == 0] = -1
              riskText = np.zeros(lenCatch).astype(str)
              riskText[risk ==-1] = "No upstream sources"
              riskText[risk == 0] = "Lowest"
              riskText[risk == 1] = "Lower"
              riskText[risk == 2] = "Medium"
              riskText[risk == 3] = "Higher"
              riskText[risk >= 5] = "Highest"
               
              outputDF["Risk Score _ " + riskName] = risk.tolist()
              outputDF["Risk Level _ " + riskName] = riskText.tolist()
              
                 
        StreamRisk (roadCCULocal, cumRoadAreaLocal, "Local Roads") 
        StreamRisk (roadCCUSH, cumRoadAreaSH, "State Highways") 
        StreamRisk (roadCCUAll, cumRoadAreaAll, "All Roads") 
        StreamRisk (urbanCCU, cumUrbArea, "Urban") 
        StreamRisk (totalCCU, cumAreaTot, "Combined") 
        
        
        """---------------------------------------------------------------------------
        Calculate coastal risks
        ---------------------------------------------------------------------------"""
        
        #add the loads from the outputs df
        
        loadList = ['cumLoadRoadZnLocal', 'cumLoadRoadCuLocal',  'cumLoadRoadZnSH',  'cumLoadRoadCuSH',\
                      'cumLoadRoadZnAll',  'cumLoadRoadCuAll',  'cumLoadUrbZn',  'cumLoadUrbCu', \
                      'cumZnLoadTot',  'cumCuLoadTot',  'cumAreaRoadLocal',  'cumAreaRoadSH',\
                      'cumRoadAreaAll',  'cumAreaUrb',  'cumAreaTot']
        
        estuaryDF = estuaryDF.join(outputDF[loadList], how = "left")
        
        
        estLength =len(estuaryDF)
        
        #convert refernece columns to Numpy arrays
        
        estTrapEff = estuaryDF['EstTrapEff'].values
        cumSedLoad = estuaryDF['cumSedLoad'].values
        
        #create RES scores from the trap efficiancy, 0 for low (<low), 3 for medium 
        #() and 5 for high (high)
        
        coastRES = np.zeros(len(estuaryDF)).astype(np.int8)
        
        coastRES[estTrapEff > TrapLow] = 3
        coastRES[estTrapEff > TrapHigh] = 5
        
        
        def CoastRisk (ZnLoadCol, CuLoadCol, cumAreaCol, riskName):
            #make arrays of load columns
            cumArea = estuaryDF[cumAreaCol].values
            ZnLoad = estuaryDF[ZnLoadCol].values
            CuLoad = estuaryDF[CuLoadCol].values
            
            #calculate the metal sediment mass concentration (mg/kg, same as g/t) 
            
            concZn = Divider(ZnLoad, cumSedLoad, estLength)
            concCu = Divider(CuLoad, cumSedLoad, estLength)
            
            estuaryDF["concZn" + riskName] = concZn.tolist()
            estuaryDF["concCU" + riskName] = concCu.tolist()    
            
            
            #calculate coastal CCU and score 1 for CCU < Low, 3 for medium and 5 where CCU > high
            
            coastCCU = concZn / ZnTEL + concCu / CuTEL
            coastCCUscore = np.ones(len(estuaryDF)).astype(np.int8)
            coastCCUscore[coastCCU > CoastLowerCCU] = 3
            coastCCUscore[coastCCU > CoastUpperCCU] = 5
             
            
            risk = coastRES * coastCCUscore
            risk[cumArea == 0] = -1
            riskText = np.zeros(estLength).astype(str)  
            riskText[(risk > 0) & (risk < 9)] = "Lower"
            riskText[risk ==-1] = "No upstream sources"
            riskText[risk == 0] = "Lowest"
            riskText[risk == 9] = "Medium"
            riskText[risk == 15] = "Higher"
            riskText[risk > 15] = "Highest"
            
            
            estuaryDF["Risk Score _ " + riskName] = risk.tolist()
            estuaryDF["Risk Level _ " + riskName] = riskText.tolist()
        
        
        #Local roads    
        
        CoastRisk('cumLoadRoadZnLocal', 'cumLoadRoadCuLocal', 'cumAreaRoadLocal', "Local Roads")
            
        CoastRisk('cumLoadRoadZnSH', 'cumLoadRoadCuSH', 'cumAreaRoadSH', "State Highways")   
        
        CoastRisk('cumLoadRoadZnAll', 'cumLoadRoadCuAll', 'cumRoadAreaAll', "All Roads")
        
        CoastRisk('cumLoadUrbZn', 'cumLoadUrbCu', 'cumAreaUrb', "Urban")
        
        CoastRisk('cumZnLoadTot', 'cumCuLoadTot', 'cumAreaTot', "Combined")
        
        
        """------------------------------------------------------------------------------
        Make the whopping great shapefiles and plot maps
        -------------------------------------------------------------------------"""
        
        if shape == 1 or jpgimage ==1:
        
            print ("Doing mapping")
            #Open the reference shapefiles
            
            print ("Opening reference Layers")
            
            
            coastGDF = gpd.read_file("InputShapes/CoastlineWGS84.shp")
            
            streamGDF = gpd.read_file("InputShapes/RiverlinesWGS84.shp")
            
            lakesGDF  = gpd.read_file("InputShapes/Lakes_1km_WGS84.shp")
            
            print ("Opening subcatchment layer (WARNING, this takes an age)")
            
            subsCatchGDF = gpd.read_file("InputShapes/SubCatchWGS84.shp")
            subsCatchGDF = subsCatchGDF.set_index("nzsegment")
              
            
            print ("Opening coastlal terminal reach layer")
            
            subsCoastGDF = gpd.read_file("InputShapes/TerminalsWGS84.shp")
            subsCoastGDF = subsCoastGDF.set_index("nzsegment")
            
        else:
            print ("No shapefiles or jpgs selected")
        
        
        def MakeShape(subsGDF, DF, environ):
        
            print ("Making shapefiles: " + environ)
           
            
            subsGDF = subsGDF.join(DF)
        
            
            zincList = ["geometry", 'genRoadZnLocal', 'cumLoadRoadZnLocal', 'genRoadZnSH', 'cumLoadRoadZnSH', \
                        'genRoadZnAll', 'cumLoadRoadZnAll',  'genUrbZn', 'cumLoadUrbZn',  'genZnLoadTot', 'cumZnLoadTot']
            
            copperList = ["geometry", 'genRoadCuLocal', 'cumLoadRoadCuLocal',  'genRoadCuSH', 'cumLoadRoadCuSH', \
                      'genRoadCuAll', 'cumLoadRoadCuAll', 'genUrbCu', 'cumLoadUrbCu', 'genCuLoadTot', 'cumCuLoadTot'] 
            
            
            riskList = ["geometry", 'Risk Score _ Local Roads', "Risk Level _ Local Roads", \
                "Risk Score _ State Highways", 'Risk Level _ State Highways', \
                "Risk Score _ All Roads", 'Risk Level _ All Roads', 'Risk Score _ Urban', \
                'Risk Level _ Urban', 'Risk Score _ Combined', 'Risk Level _ Combined']
            
            
            labelDict = {'genRoadZnLocal': "GenZnLocal", "cumLoadRoadZnLocal": "InstrZnLocal", \
                'genRoadCuLocal': "GenCuLocal", "cumLoadRoadCuLocal":  "InstrCuLocal", \
                'genRoadZnSH': "GenZnSH", "cumLoadRoadZnSH": "InstrZnSH", 'genRoadCuSH':"GenCuSH", \
                "cumLoadRoadCuSH": "InstrCuSH", 'genRoadZnAll': "GenZnRoads", "cumLoadRoadZnAll": 
                "InstrZnRoads", 'genRoadCuAll': "GenCuRoads", "cumLoadRoadCuAll": "InstrCuRoads", \
                'genUrbZn': "GenZn", "cumLoadUrbZn": "InstrZnUrb", 'genUrbCu': "GenCuUrban", \
                "cumLoadUrbCu": "InstrCuUrb", 'genZnLoadTot': "GenZnComb", "cumZnLoadTot": \
                "InstrZnComb", 'genCuLoadTot': "GenCuComb", "cumCuLoadTot":  "InstrCuComb",\
                'Risk Score _ Local Roads' : "LocalRS", "Risk Level _ Local Roads" : "LocalRL", \
                "Risk Score _ State Highways": "SHRS", 'Risk Level _ State Highways' : "SHRL", \
                "Risk Score _ All Roads" : "RoadsRS", 'Risk Level _ All Roads': "RoadsRL", \
                'Risk Score _ Urban': "UrbanRS", 'Risk Level _ Urban': "UrbanRl", 'Risk Score _ Combined': "CombRS",\
                'Risk Level _ Combined': "CombRL"}
            
                    
            #Make the shapefiles
            
            def MakeFile (fileName, fieldList):
                
                print("Making shapefile: ", fileName)
                
                shapeGDF = subsGDF[fieldList].copy(deep = True)
                
                if fileName == "ZincLoads" or fileName == "CopperLoads":
                    loadLen = len(fieldList)
                    loadList = fieldList[1:loadLen]
                    
                    for load in loadList:
                        shapeGDF[load] /= 1000
                
                       
                shapeGDF = shapeGDF.rename(columns = labelDict)
                
                shapeGDF = shapeGDF.reset_index()
                       
                if os.path.isfile(outputPath + fileName + ".cpg"):
                    os.remove(outputPath + fileName + ".cpg")
                
                if os.path.isfile(outputPath + fileName + ".dbf"):
                    os.remove(outputPath + fileName + ".dbf")
                    
                if os.path.isfile(outputPath + fileName + ".prj"):
                    os.remove(outputPath + fileName + ".prj")
                    
                if os.path.isfile(outputPath + fileName + ".shp"):
                    os.remove(outputPath + fileName + ".shp")
                    
                if os.path.isfile(outputPath + fileName + ".shx"):
                    os.remove(outputPath + fileName + ".shx")
                    
                shapeGDF.to_file(outputPath + fileName + ".shp")
                       
            if shape == 1:
                if environ == "Streams":
                    MakeFile("Risk_Streams", riskList)
                    MakeFile("ZincLoads", zincList)
                    MakeFile("CopperLoads", copperList)
                else:
                    MakeFile("RiskMap_Coast", riskList)
            
                                      
            def MakeMap (riskScore, riskName):
                print ("Making jpg: " + riskName + environ)
                
                RS = subsGDF[riskScore]      
                
                
                if environ == "Streams":
                                           
                    noRisk = subsGDF[(RS == -1)] 
                    lowestRisk = subsGDF[(RS == 0)] 
                    lowerRisk = subsGDF[(RS == 1)] 
                    medRisk = subsGDF[(RS == 2)] 
                    higherRisk = subsGDF[(RS == 3)] 
                    higestRisk = subsGDF[(RS == 5)]
        
                else:
                    noRisk = subsGDF[(RS == -1)] 
                    lowestRisk = subsGDF[(RS == 0)] 
                    lowerRisk = subsGDF[(RS > 1) & (RS < 9)] 
                    medRisk = subsGDF[(RS == 9)] 
                    higherRisk = subsGDF[(RS == 15)] 
                    higestRisk = subsGDF[(RS > 5)]
                    
                
                base = coastGDF.plot (figsize = (10,10), color = "black", linewidth = 0.4)
                
                plt.title("Risk Level: " + riskName, fontsize = 11)
                
                
                noRisk.plot(ax = base, color = colourList[0])
                lowestRisk.plot(ax = base, color = colourList[1])
                lowerRisk.plot(ax = base, color = colourList[2])
                medRisk.plot(ax = base, color = colourList[3])
                higherRisk.plot(ax = base, color = colourList[4])
                higestRisk.plot(ax = base, color = colourList[5])
                
                streamGDF.plot (ax = base, color = "blue", linewidth = 0.4)
                
                lakesGDF.plot (ax = base, color = "blue")
                
                if os.path.isfile(outputPath + "RiskMap" + riskName + environ+ ".jpg"):
                    os.remove(outputPath + "RiskMap" + riskName + environ + ".jpg")
                
                plt.savefig(outputPath + "RiskMap" + riskName + environ + ".jpg")
                
            if jpgimage == 1:
        
                MakeMap ('Risk Score _ Local Roads', "LocalRoads")
                MakeMap ( "Risk Score _ State Highways", "StateHighways")
                MakeMap ("Risk Score _ All Roads", "AllRoads")
                MakeMap ('Risk Score _ Urban', "Urban")
                MakeMap ('Risk Score _ Combined', "Combined")
                
        if shape == 1 or jpgimage == 1:   
            
            MakeShape(subsCatchGDF, outputDF, "Streams")
            MakeShape(subsCoastGDF, estuaryDF, "Coast")
        
        
        """----------------------------------------------------------------------
        Make pivots
        ---------------------------------------------------------------------------"""
    
        print ("Making summary pivots")
        
        
        #add counter to output DF
        outputDF["Counter"] = 1
        estuaryDF["Counter"] = 1
        
        def PivotMaker (riskCol, riskName, resultDF, environ):
            
            if environ == "Streams":
                pivot = pd.pivot_table(resultDF, index = [riskCol], values = ["Counter", \
                                        "StreamLength_km"], aggfunc = sum).astype(np.int32)
                pivot = pivot.rename(columns = {"Counter": riskName + " _ segments", \
                        "StreamLength_km": riskName + " _ stream length (km)"})
                    
            else:
                pivot = pd.pivot_table(resultDF, index = [riskCol], values = ["Counter"], aggfunc = sum)
                pivot = pivot.rename(columns = {"Counter": riskName + " _ terminals"})
                
            
            #reorder rows
            
            levelList = ["Lowest", "Lower", "Medium", "Higher", "Highest", "No upstream sources"]
            
            pivot = pivot.reindex(levelList)
            
            #rename index
            
            pivot = pivot.rename_axis("Risk Level")
                
            #add total rows
            
            pivot = pivot.append(pivot.sum().rename("Total"))
            
            
            #add % column
            
            if environ == "Streams":
                
                eligibleSeg = pivot.loc["Total", riskName + " _ segments"] \
                    - pivot.loc["No upstream sources", riskName+ " _ segments"]
                
                pivot.loc["Sum eligible", (riskName + " _ segments")] = eligibleSeg
                
                eligibleLen = pivot.loc["Total", riskName + " _ stream length (km)"] \
                    - pivot.loc["No upstream sources", riskName + " _ stream length (km)"]
                    
                           
                pivot.loc["Sum eligible", (riskName + " _ stream length (km)")] = eligibleLen
                
                    
                pivot["Percent eligible length: " + riskName] = np.round(pivot[riskName + " _ stream length (km)"] / eligibleLen * 100,1)
                
                # #reorder
                
                # pivot =pivot[[riskName + " _ segments", "Percent eligible: " + riskName, \
                              # riskName + " _ stream length (km)"]]
                
                #put in blanks where it makes no sence to have percentages
                
                pivot.loc["No upstream sources", ("Percent eligible length: " + riskName)] = np.nan
                
                pivot.loc["Total", ("Percent eligible length: " + riskName)] = np.nan
                
                pivot.loc["Sum eligible", ("Percent eligible length: " + riskName)] = np.nan
                
            else:
                eligible = pivot.loc["Total", riskName + " _ terminals"] \
                    - pivot.loc["No upstream sources", riskName + " _ terminals"]
                pivot.loc["Sum eligible"] = eligible
                
                pivot["Percent eligible terminals: " + riskName] = np.round(pivot[riskName + " _ terminals"] / eligible * 100,1)
                
                pivot.loc["No upstream sources", ("Percent eligible terminals: " + riskName)] = np.nan
                
                pivot.loc["Total", ("Percent eligible terminals: " + riskName)] = np.nan
                
                pivot.loc["Sum eligible", ("Percent eligible terminals: " + riskName)] = np.nan
            
            return pivot
        
        """----------------------------------------------------------------------------
        RMake function to Export to Excel
        ----------------------------------------------------------------------------"""   
        
        def WorksheetMaker (worksheetName, DF, environ):
            
            DF.to_excel(writer,sheet_name = worksheetName, startrow = 1, header = False)
            
            # Get the xlsxwriter workbook and worksheet objects.
            workbook  = writer.book
            worksheet = writer.sheets[worksheetName]
            
            # Add a header format.
            headerFormat = workbook.add_format({'bold': True, 'text_wrap': True, 'valign': 'top',\
                'align': 'center',  'fg_color': '#ededed', 'border': 1})
            
            # Write the column headers with the defined format.
            for col_num, value in enumerate(DF.columns.values):
                worksheet.write(0, col_num + 1, value, headerFormat)
                
            
            worksheet.write("A1", "Risk Level", headerFormat)
            
            #add formatting and set cell widths (had to use conditional formatting to cover range)
                                             
            worksheet.set_column("B:P", 17)
            
            worksheet.set_column("A:A", 21)
            
                    
            lowestFormat =  workbook.add_format({"font_color": "black", "bg_color": colourList[1], "border":1}) #green
                                                 
            lowerFormat = workbook.add_format({"font_color": fontColour, "bg_color": colourList[2], "border":1}) #yellow/green
                                                 
            mediumFormat = workbook.add_format({"font_color": fontColour, "bg_color": colourList[3], "border":1}) #yellow
                                              
            higherFormat = workbook.add_format({"font_color": fontColour, "bg_color": colourList[4], "border":1}) #oranage
                                                 
            highestFormat = workbook.add_format({"font_color": fontColour, "bg_color": colourList[5], "border":1}) #red 
                                                 
            noneFormat = workbook.add_format({"bg_color": colourList[0], "border":1}) #blue 
            
            sumFormat = workbook.add_format({"border":1}) 
            
            #apply the formats to the relevant ranges        
            
            if environ == "Streams":
                                              
                worksheet.conditional_format("B2:P2", {"type":"cell", "criteria":"!=", "value": -1, "format":lowestFormat})
                
                worksheet.conditional_format("B3:P3", {"type":"cell", "criteria":"!=", "value": -1, "format":lowerFormat})
                
                worksheet.conditional_format("B4:P4", {"type":"cell", "criteria":"!=", "value": -1, "format":mediumFormat})
                
                worksheet.conditional_format("B5:P5", {"type":"cell", "criteria":"!=", "value": -1, "format":higherFormat})
                
                worksheet.conditional_format("B6:P6", {"type":"cell", "criteria":"!=", "value": -1, "format":highestFormat})
                
                worksheet.conditional_format("B7:P7", {"type":"cell", "criteria":"!=", "value": -1, "format":noneFormat})
                
                worksheet.conditional_format("B8:P9", {"type":"cell", "criteria":"!=", "value": -1, "format":sumFormat})
            
            else:
                worksheet.conditional_format("B2:K2", {"type":"cell", "criteria":"!=", "value": -1, "format":lowestFormat})
                
                worksheet.conditional_format("B3:K3", {"type":"cell", "criteria":"!=", "value": -1, "format":lowerFormat})
                
                worksheet.conditional_format("B4:K4", {"type":"cell", "criteria":"!=", "value": -1, "format":mediumFormat})
                
                worksheet.conditional_format("B5:K5", {"type":"cell", "criteria":"!=", "value": -1, "format":higherFormat})
                
                worksheet.conditional_format("B6:K6", {"type":"cell", "criteria":"!=", "value": -1, "format":highestFormat})
                
                worksheet.conditional_format("B7:K7", {"type":"cell", "criteria":"!=", "value": -1, "format":noneFormat})
                
                worksheet.conditional_format("B8:K9", {"type":"cell", "criteria":"!=", "value": -1, "format":sumFormat})
            
            
            #Make a summary chart
            #first transpose the table and add to the spreadsheet  (this will be hidden) 
               
            if environ == "Streams":
                chartDF = DF[['Local Roads _ stream length (km)','State Highways _ stream length (km)', \
                'All Roads _ stream length (km)', "Urban _ stream length (km)", "Combined _ stream length (km)"]]
                
                headDict ={'Local Roads _ stream length (km)': "Local Roads",'State Highways _ stream length (km)': "State Highways", \
                'All Roads _ stream length (km)': "All roads", "Urban _ stream length (km)": "Urban", "Combined _ stream length (km)": "Combined"}
                
                chartDF =  chartDF.rename(columns = headDict)
                
            else:
                chartDF = DF.drop(columns = ['Percent eligible terminals: Local Roads',\
                'Percent eligible terminals: State Highways','Percent eligible terminals: All Roads','Percent eligible terminals: Urban', \
                'Percent eligible terminals: Combined'])
                    
                headDict ={'Local Roads _ terminals': "Local Roads",'State Highways _ terminals': "State Highways", 
                'All Roads _ terminals': "All roads", "Urban _ terminals": "Urban", "Combined _ terminals": "Combined"}
                
                chartDF =  chartDF.rename(columns = headDict)
                
            chartDF = chartDF.transpose() 
            
            chartDF = chartDF.drop(columns = [ 'No upstream sources',  'Total',  'Sum eligible'])  
             
            chartDF.to_excel(writer,sheet_name = worksheetName, startcol = 120)
            
                    
            chart = workbook.add_chart({"type" : "column"})
                    
            
            chart.add_series({"categories": [worksheetName, 1, 120, 5, 120], "line": {"color": "black"}, \
                "values":[worksheetName, 1, 121, 5, 121], "name": [worksheetName, 0, 121], 'fill': {'color': colourList[1]}})
                               
            chart.add_series({"categories": [worksheetName, 1, 120, 5, 120], "line": {"color": "black"},
                "values":[worksheetName, 1, 122, 5, 122], "name": [worksheetName, 0, 122], 'fill': {'color': colourList[2]}})
                        
            chart.add_series({"categories":[worksheetName, 1, 120, 5, 120], "line": {"color": "black"}, 
                "values":[worksheetName, 1, 123, 5, 123], "name": [worksheetName, 0, 123], 'fill': {'color': colourList[3]}})
                        
            chart.add_series({"categories":[worksheetName, 1, 120, 5, 120], "line": {"color": "black"},
                "values":[worksheetName, 1, 124, 5, 124], "name": [worksheetName, 0, 124], 'fill': {'color': colourList[4]}})
                        
            chart.add_series({"categories":[worksheetName, 1, 120, 5, 120], "line": {"color": "black"},
                "values":[worksheetName, 1, 125, 5, 125], "name": [worksheetName, 0, 125], 'fill': {'color': colourList[5]}})
                        
            
            chart.set_x_axis({"name": "Risk Level", 'name_font': {'size': 12, 'bold': True},})
            
            if environ == "Streams":
                chart.set_y_axis({'name_font': {'size': 12, 'bold': True}, "name": "Eligible Lengths in risk level (km)"})
                
            else:
                chart.set_y_axis({'name_font': {'size': 12, 'bold': True}, "name": "Number of terminal segments"})
            
            
            
            chart.set_title({'name_font': {'size': 16, 'bold': True}, "name": "Risk Levels : " + worksheetName})
            
            chart.set_size({'x_scale': 2, 'y_scale': 1.5})
            
            worksheet.insert_chart('A12', chart)
            
            
            #Make % chart
            
            if environ =="Streams":
                chartDF = DF[['Percent eligible length: Local Roads','Percent eligible length: State Highways', \
                              'Percent eligible length: All Roads', "Percent eligible length: Urban", "Percent eligible length: Combined"]]
                
                headDict = {'Percent eligible length: Local Roads': "Local Roads",'Percent eligible length: State Highways': 'State Highways', \
                              'Percent eligible length: All Roads': "All Roads", "Percent eligible length: Urban": "Urban", \
                              "Percent eligible length: Combined": "Combined"}
                
                chartDF =  chartDF.rename(columns = headDict)
                
                
            else:
                chartDF = DF[['Percent eligible terminals: Local Roads', 'Percent eligible terminals: State Highways',\
                              'Percent eligible terminals: All Roads','Percent eligible terminals: Urban', \
                              'Percent eligible terminals: Combined']]
                
                headDict = {'Percent eligible terminals: Local Roads': "Local Roads",'Percent eligible terminals: State Highways': 'State Highways', 
                              'Percent eligible terminals: All Roads': "All Roads", "Percent eligible terminals: Urban": "Urban", 
                              "Percent eligible terminals: Combined": "Combined"}
                
                chartDF =  chartDF.rename(columns = headDict)
            
            chartDF = chartDF.transpose() 
            
            chartDF = chartDF.drop(columns = [ 'No upstream sources',  'Total',  'Sum eligible'])  
             
            chartDF.to_excel(writer,sheet_name = worksheetName, startcol = 130)
            
            #Make a summary chart
            
            chart = workbook.add_chart({"type" : "column"})
            
            chart.add_series({"categories":[worksheetName, 1, 130, 5, 130], "line": {"color": "black"},
                "values":[worksheetName, 1, 131, 5, 131], "name": [worksheetName, 0, 131], 'fill': {'color':colourList[1]}})
                        
            chart.add_series({"categories":[worksheetName, 1, 130, 5, 130], "line": {"color": "black"},
                "values":[worksheetName, 1, 132, 5, 132], "name": [worksheetName, 0, 132], 'fill': {'color': colourList[2]}})
                                
            chart.add_series({"categories":[worksheetName, 1, 130, 5, 130], "line": {"color": "black"}, 
                "values":[worksheetName, 1, 133, 5, 133], "name": [worksheetName, 0, 133], 'fill': {'color': colourList[3]}})
                        
            chart.add_series({"categories":[worksheetName, 1, 130, 5, 130], "line": {"color": "black"},
                "values":[worksheetName, 1, 134, 5, 134], "name": [worksheetName, 0, 134], 'fill': {'color': colourList[4]}})
                        
            chart.add_series({"categories":[worksheetName, 1, 130, 5, 130], "line": {"color": "black"},
                "values":[worksheetName, 1, 135, 5, 135], "name": [worksheetName, 0, 135], 'fill': {'color': colourList[5]}})
                        
                        
            
            chart.set_x_axis({"name": "Risk Level", 'name_font': {'size': 12, 'bold': True},})
            
            chart.set_y_axis({'name_font': {'size': 12, 'bold': True}, "name": "Percentage"})
            
            chart.set_title({'name_font': {'size': 16, 'bold': True}, "name": "Risk Levels (%) : " + worksheetName})
            
            chart.set_size({'x_scale': 2, 'y_scale': 1.5})
            
            worksheet.insert_chart('I12', chart)
            
            
            #Hide the chart reference cells by changing font colour
            hideFormat = workbook.add_format({'font_color': 'white', "border": 0, "border_color": 0 })
            
            worksheet.conditional_format("DQ1:EH6", {"type":"cell", "criteria":"!=", "value": -1, "format":hideFormat})
            
        
        
        """------------------------------------------------------------------------------
        Add Maps to workbook Function
        -------------------------------------------------------------------------------"""
        
        def InsertMaps (mapList):
            workbook  = writer.book
              
            Maps = workbook.add_worksheet("Maps")
            
            lowestFormat =  workbook.add_format({"bg_color": colourList[1], "border":1}) #green
                                                     
            lowerFormat = workbook.add_format({"font_color": fontColour, "bg_color": colourList[2], "border":1}) #yellow/green
                                                 
            mediumFormat = workbook.add_format({"font_color": fontColour, "bg_color": colourList[3], "border":1}) #yellow
                                                  
            higherFormat = workbook.add_format({"font_color": fontColour, "bg_color": colourList[4], "border":1}) #oranage
                                                     
            highestFormat = workbook.add_format({"font_color": fontColour, "bg_color": colourList[5], "border":1}) #red   
            
            noneFormat = workbook.add_format({"bg_color": colourList[0], "border":1}) #blue 
            
            Maps.write("A1", "Legend for all maps:")
            
            Maps.write ("B1", "Lowest", lowestFormat)
            
            Maps.write ("C1", "Lower", lowerFormat)
            
            Maps.write ("D1", "Medium", mediumFormat)
            
            Maps.write ("E1", "Higher", higherFormat)
            
            Maps.write ("F1", "Highest", highestFormat)
            
            Maps.write ("G1", "No upstream sources", noneFormat)
            
            Maps.set_column("A:A", 20)
            Maps.set_column("G:G", 20)
            
            
            Maps.insert_image("A3", outputPath + mapList[0])
            
            Maps.insert_image("N3", outputPath + mapList[1])
            
            Maps.insert_image("A45", outputPath + mapList[2])
            
            Maps.insert_image("N45", outputPath + mapList[3])
            
            Maps.insert_image("A87", outputPath + mapList[4])
        
        """----------------------------------------------------------------------------
        Cycle through regions for streams
        ----------------------------------------------------------------------------"""
               
        print ("Making stream spreadsheet")
        #Make the spreadsheet
        
        fileName = "StreamRisk_Summary.xlsx"  
               
        if os.path.isfile(outputPath + fileName):
            os.remove(outputPath + fileName)
        
        writer = pd.ExcelWriter(outputPath + fileName, engine='xlsxwriter')
        
        #make National summaries
        
        localPivotStreams = PivotMaker ('Risk Level _ Local Roads', "Local Roads", outputDF, "Streams")
        
        SHPivotStreams = PivotMaker ('Risk Level _ State Highways', "State Highways", outputDF, "Streams")
        
        allRoadsPivotStreams = PivotMaker ('Risk Level _ All Roads', "All Roads", outputDF, "Streams")
        
        urbPivotStreams = PivotMaker ('Risk Level _ Urban', "Urban", outputDF, "Streams")
        
        combinedPivotStreams = PivotMaker ('Risk Level _ Combined', "Combined", outputDF, "Streams")
        
        DFList = [SHPivotStreams, allRoadsPivotStreams, urbPivotStreams, combinedPivotStreams]
        
        streamSummaryDF = localPivotStreams.join(DFList)
        
        WorksheetMaker ("National", streamSummaryDF, "Streams")
        
        #Add the maps only if Jpgs are selected
        
        if jpgimage == 1:
        
            mapList = ['RiskMapLocalRoadsStreams.jpg' , 'RiskMapStateHighwaysStreams.jpg', 
                        'RiskMapAllRoadsStreams.jpg', 'RiskMapUrbanStreams.jpg', 'RiskMapCombinedStreams.jpg']
            
            InsertMaps(mapList)
        
        #Make regional summaries
        
        regionList = ['Auckland', 'Bay of Plenty', 'Canterbury', 'Gisborne', 'Hawkes Bay',\
            'Manawatu-Whanganui', 'Nelson-Tasman', 'Marlborough', 'Northland', 'Otago', \
            'Southland', 'Taranaki', 'Waikato', 'Wellington', 'West Coast']
        
        for region in regionList:
            regionDF = outputDF[outputDF.Region == region]
            localPivotStreamsReg = PivotMaker ('Risk Level _ Local Roads', "Local Roads", regionDF, "Streams")
        
            SHPivotStreamsReg = PivotMaker ('Risk Level _ State Highways', "State Highways", regionDF, "Streams")
        
            allRoadsPivotStreamsReg = PivotMaker ('Risk Level _ All Roads', "All Roads", regionDF, "Streams")
        
            urbPivotStreamsReg = PivotMaker ('Risk Level _ Urban', "Urban", regionDF, "Streams")
        
            combinedPivotStreamsReg = PivotMaker ('Risk Level _ Combined', "Combined", regionDF, "Streams")
        
            DFList = [SHPivotStreamsReg, allRoadsPivotStreamsReg, urbPivotStreamsReg, combinedPivotStreamsReg]
        
            streamSummaryDFReg = localPivotStreamsReg.join(DFList)
            
            WorksheetMaker (region, streamSummaryDFReg, "Streams")
            
        
        writer.save()
        
    
        """----------------------------------------------------------------------------
        Cycle through regions for coast
        ----------------------------------------------------------------------------"""
        
        print ("making coast spreadsheet")
        #Make the spreadsheet
        
        fileName = "CoastRisk_Summary.xlsx"
          
               
        if os.path.isfile(outputPath + fileName):
            os.remove(outputPath + fileName)
        
        writer = pd.ExcelWriter(outputPath + fileName, engine='xlsxwriter')
        
        #Coast
        
        localPivotCoast = PivotMaker ('Risk Level _ Local Roads', "Local Roads", estuaryDF, "Coast")
        
        SHPivotCoast = PivotMaker ('Risk Level _ State Highways', "State Highways", estuaryDF, "Coast")
        
        allRoadsPivotCoast = PivotMaker ('Risk Level _ All Roads', "All Roads", estuaryDF, "Coast")
        
        urbPivotCoast = PivotMaker ('Risk Level _ Urban', "Urban", estuaryDF, "Coast")
        
        combinedPivotCoast = PivotMaker ('Risk Level _ Combined', "Combined", estuaryDF, "Coast")
        
        DFList = [SHPivotCoast, allRoadsPivotCoast, urbPivotCoast, combinedPivotCoast]
        
        coastSummaryDF = localPivotCoast.join(DFList)
        
        WorksheetMaker ("National", coastSummaryDF, "Coast")
        
        #Add the mapssv
        
        if jpgimage == 1:
        
            mapList = ['RiskMapLocalRoadsCoast.jpg' , 'RiskMapStateHighwaysCoast.jpg', 
                    'RiskMapAllRoadsCoast.jpg', 'RiskMapUrbanCoast.jpg', 'RiskMapCombinedCoast.jpg']
        
            InsertMaps (mapList)
        
    
        for region in regionList:
            regionDF = estuaryDF[estuaryDF.Region == region]
            
            localPivotCoastReg = PivotMaker ('Risk Level _ Local Roads', "Local Roads", regionDF, "Coast")
        
            SHPivotCoastReg = PivotMaker ('Risk Level _ State Highways', "State Highways", regionDF, "Coast")
        
            allRoadsPivotCoastReg = PivotMaker ('Risk Level _ All Roads', "All Roads", regionDF, "Coast")
        
            urbPivotCoastReg = PivotMaker ('Risk Level _ Urban', "Urban", regionDF, "Coast")
        
            combinedPivotCoastReg = PivotMaker ('Risk Level _ Combined', "Combined", regionDF, "Coast")
            
            DFListReg = [SHPivotCoastReg, allRoadsPivotCoastReg, urbPivotCoastReg, combinedPivotCoastReg]
        
            coastSummaryDFReg = localPivotCoastReg.join(DFListReg)
            
            WorksheetMaker (region, coastSummaryDFReg, "Coast")
        
        writer.save()
    
        """-------------------------------------------------------------------------------
        Finally, make CSVs of results by reach
        -------------------------------------------------------------------------"""
        print ("Making CSVs")
        
        def MakeCSV (csvName, dataframe):
                       
            if os.path.isfile(csvName):
                os.remove(outputPath + csvName)
                
            dataframe.to_csv(outputPath + csvName)
        
        #Streams first
        
        print ("Streams")
        
        # copy and keep only the fields to report
            
        # copy and keep only the fields to report
        
        colList = ['Region', 'genRoadZnLocal', 'cumLoadRoadZnLocal', 'concRoadZnLocal', 'genRoadCuLocal',\
            'cumLoadRoadCuLocal', 'concRoadCuLocal','genRoadZnSH', 'cumLoadRoadZnSH', 'concRoadZnSH', \
            'genRoadCuSH', 'cumLoadRoadCuSH', 'concRoadCuSH', 'genRoadZnAll', 'cumLoadRoadZnAll', 'concRoadZnAll', \
            'genRoadCuAll', 'cumLoadRoadCuAll', 'concRoadCuAll', 'genUrbZn', 'cumLoadUrbZn', 'concUrbZn', \
            'genUrbCu', 'cumLoadUrbCu', 'concUrbCu', 'genZnLoadTot', 'cumZnLoadTot', 'concZnTot', \
            'genCuLoadTot', 'cumCuLoadTot', 'concCuTot', 'Risk Score _ Local Roads', \
            'Risk Level _ Local Roads', 'Risk Score _ State Highways', 'Risk Level _ State Highways', \
            'Risk Score _ All Roads', 'Risk Level _ All Roads', 'Risk Score _ Urban', 'Risk Level _ Urban', 
            'Risk Score _ Combined', 'Risk Level _ Combined']
            
        csvStreamsDF = outputDF[colList].copy(deep = True)   
            
        #Convert loads to kg
            
        loadList = ['genRoadZnLocal', 'cumLoadRoadZnLocal', 'genRoadCuLocal', 'cumLoadRoadCuLocal',  \
                    'genRoadZnSH', 'cumLoadRoadZnSH',  'genRoadCuSH', 'cumLoadRoadCuSH', 'genRoadZnAll', \
                      'genRoadCuAll', 'cumLoadRoadZnAll',  'cumLoadRoadCuAll', 'genUrbZn', 'cumLoadUrbZn',  \
                      'genUrbCu', 'cumLoadUrbCu', 'genZnLoadTot', 'cumZnLoadTot', 'genCuLoadTot', 'cumCuLoadTot']
        
        for load in loadList:
            csvStreamsDF[load] /= 1000
            
           
        #add nice headers
            
        headerDictStream = {'genRoadZnLocal': "Generated Zn load (kg/y) _ Local Roads", \
            "cumLoadRoadZnLocal": "Instream Zn load (kg/y) _ Local Roads", \
            "concRoadZnLocal": "Zn concentration (mg/l) _ Local Roads", 'genRoadCuLocal': "Generated Cu load (kg/y) _ Local Roads" ,\
            "cumLoadRoadCuLocal":  "Instream Cu load (kg/y) _ Local Roads", "concRoadCuLocal": "Cu concentration (mg/l)_Local Roads", \
          'genRoadZnSH': "Generated Zn load (kg/y) _ State Highways", "cumLoadRoadZnSH": "Instream Zn load (kg/y) _ State Highways", \
          "concRoadZnSH":  "Zn concentration (mg/l) _ State Highways", 'genRoadCuSH':"Generated Cu load (kg/y) _ State Highways", \
            "cumLoadRoadCuSH": "Instream Cu load (kg/y) _ State Highways",  "concRoadCuSH": "Cu concentration (mg/l) _ State Highways", \
            'genRoadZnAll': "Generated Zn load (kg/y) _ All Roads", "cumLoadRoadZnAll": "Instream Zn load (kg/y) _ All Roads", \
            "concRoadZnAll": "Zn concentration (mg/l) _ All Roads", 'genRoadCuAll': "Generated Cu load (kg/y) _ All Roads", 
          "cumLoadRoadCuAll": "Instream Cu load (kg/y) _ All Roads", "concRoadCuAll":  "Cu concentration (mg/l) _ All Roads", \
          'genUrbZn': "Generated Zn load (kg/y) _ Urban", "cumLoadUrbZn": "Instream Zn load (kg/y) _ Urban","concUrbZn": \
          "Zn concentration (mg/l) _ Urban", 'genUrbCu': "Generated Cu load (kg/y) _ Urban", "cumLoadUrbCu": "Instream Cu load (kg/y) _ Urban", \
          "concUrbCu": "Cu concentration (mg/l) _ Urban", 'genZnLoadTot': "Generated Zn load (kg/y) _ Combined",\
          "cumZnLoadTot": "Instream Zn load (kg/y) _ Combined",  "concZnTot": "Zn concentration (mg/l) _ Combined", \
          'genCuLoadTot': "Generated Cu load (kg/y) _ Combined", "cumCuLoadTot":  "Instream Cu load (kg/y) _ Combined", \
          "concCuTot": "Cu concentration (mg/l) _ Combined"}
           
               
        csvStreamsDF =  csvStreamsDF.rename(columns = headerDictStream)
         
        MakeCSV("StreamRisk_segments.csv", csvStreamsDF)
        
        #Coast
        print ("Coast")
        
        colList = ['Region',  'Estuary', 'cumLoadRoadZnLocal', 'concZnLocal Roads',  \
          'cumLoadRoadCuLocal', 'concCULocal Roads',  'cumLoadRoadZnSH', 'concZnState Highways', \
          'cumLoadRoadCuSH', 'concCUState Highways',  'cumLoadRoadZnAll', 'concZnAll Roads',  \
          'cumLoadRoadCuAll', 'concCUAll Roads',  'cumLoadUrbZn', 'concZnUrban',   'cumLoadUrbCu', \
          'concCUUrban',  'cumZnLoadTot', 'concZnCombined',  'cumCuLoadTot', 'concCUCombined', \
          'Risk Score _ Local Roads',  'Risk Level _ Local Roads',  'Risk Score _ State Highways',  \
          'Risk Level _ State Highways',  'Risk Score _ All Roads',  'Risk Level _ All Roads',  \
          'Risk Score _ Urban',  'Risk Level _ Urban',  'Risk Score _ Combined',  'Risk Level _ Combined'] 
        
        csvCoastDF = estuaryDF[colList].copy(deep = True)
        
        #Convert loads to kg
        
        loadList = ['cumLoadRoadZnLocal', 'cumLoadRoadCuLocal', 'cumLoadRoadZnSH', 'cumLoadRoadCuSH',  \
                      'cumLoadRoadZnAll',  'cumLoadRoadCuAll', 'cumLoadUrbZn',  'cumLoadUrbCu', \
                      'cumZnLoadTot', 'cumCuLoadTot']
        
        for load in loadList:
            csvCoastDF[load] /= 1000
            
        # add nice headers
        
        headerDictCoast = {"Estuary": "Hydrosystem", 'cumLoadRoadZnLocal': 'Discharged Zn load (kg/y) _ Local Roads', 
            'concZnLocal Roads': 'Zn concentration (mg/kg) _ Local Roads', 
            'cumLoadRoadCuLocal': 'Discharged Cu load (kg/y) _ Local Roads', 'concCULocal Roads': 
            'Cu concentration (mg/kg)_Local Roads', 'cumLoadRoadZnSH': 'Discharged Zn load (kg/y) _ State Highways', 
            'concZnState Highways': 'Zn concentration (mg/kg) _ State Highways', 'cumLoadRoadCuSH': 
            'Discharged Cu load (kg/y) _ State Highways', 'concCUState Highways': 'Cu concentration (mg/kg) _ State Highways', 
            'cumLoadRoadZnAll': 'Discharged Zn load (kg/y) _ All Roads', 'concZnAll Roads': 'Zn concentration (mg/kg) _ All Roads', 
            'cumLoadRoadCuAll': 'Discharged Cu load (kg/y) _ All Roads', 'concCUAll Roads': 'Cu concentration (mg/kg) _ All Roads', 
            'cumLoadUrbZn': 'Discharged Zn load (kg/y) _ Urban', 'concZnUrban': 'Zn concentration (mg/kg) _ Urban', 
            'cumLoadUrbCu': 'Discharged Cu load (kg/y) _ Urban', 'concCUUrban': 'Cu concentration (mg/kg) _ Urban', 
            'cumZnLoadTot': 'Discharged Zn load (kg/y) _ Combined', 'concZnCombined': 'Zn concentration (mg/kg) _ Combined', 
            'cumCuLoadTot':  'Discharged Cu load (kg/y) _ Combined', 'concCUCombined': 'Cu concentration (mg/kg) _ Combined', }
        
        csvCoastDF =  csvCoastDF.rename(columns = headerDictCoast)
        
        MakeCSV("CoastalRisk_terminals.csv", csvCoastDF)
        
        RAMMsegmentDF["Capacity"] = capacity.tolist()
        MakeCSV("Capacity.csv", RAMMsegmentDF)
        
        print ("It took {:.3f} seconds to do the run".format(time.time() - codeTime))
        
        endMessage = "Ready to make a new scenario"
        
    
        
            
    return endMessage




