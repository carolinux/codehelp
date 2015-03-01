#-------------------------------------------------------------------------------
# Name:        Tanalyst2CSV
# Purpose:     Reads tracking data from Lund University T-analyst software format and writes to plain text for easy import to GIS
#
# Author:      Soren Zebitz Nielsen, szn@ign.ku.dk
#
# Created:     05-02-2015
# Copyright:   (c) Soren Zebitz Nielsen 2015
#
# Note:        There is a rounding bug for milliseconds in that it both can yield  .x66000 and .x67000 and the error is unsystematic
#              The solution to that problem is to run a simple search and replace for either 66000' or 67000' in the output .txt (CSV) file depending on which rounding format is preferred.
#-------------------------------------------------------------------------------

# Imports
import os, os.path
import sys
from datetime import datetime ,timedelta
from time import time as wallClock
from common import *

# Settings
path = "C:\\Users\\lvp326\\Dropbox\\PhD\\Urban_Movement\\Code".replace("\\", "/")
fn = "00100002" ## Remember to set change videoData and videoStartTime below to match the current file
inFileName = fn + ".txt"
inFile = open(os.path.join(path,inFileName), "r") # os path join is portable across operating
# systems

outFileName = fn + "_out.txt"
outFile = open(os.path.join(path,outFileName), "w")

outFileNameBasic = fn + "_out_Basic.txt"
outFileBasic = open(os.path.join(path,outFileNameBasic), "w")

outStatFileName = fn + "_outStat.txt"
outStatFile = open(os.path.join(path, outStatFileName), "w")

startExecusionTime = wallClock()
backFrameLengthSec = 5 ## Frames back in time use for speed calculations etc.

frameDict = {}
delim = ";"
ping = "'"

# Set X and Y coordinates offsets
Xoffset = 724660
Yoffset = 6176550

# Set video start time and date
videoDate="14-06-2013"
videoStartTime = "13:00:00.000"
videoFrameRate = 30 ## The rounding to milliseconds procedure only work correctly for 30 FPS video




## ---------------------------------------------
# Main
line = inFile.readline()
inLineCount = 0
subjectId = 0
subjectLineCount = 0

dt=formatDateTime(videoDate,videoStartTime)
dateTime = datetime(dt[2], dt[1], dt[0], dt[3], dt[4], dt[5], dt[6])
deltaTime=timedelta(seconds=1)/videoFrameRate

while line:
    lstLine = line.split()
    if len(lstLine) > 1:
        if lstLine[0] == "Type:":
            roadUserType = lstLine[1] ## get info on road user type
            subjectId += 1 ## set subjectId
            subjectLineCount = 0 ## reset subjectLineCount before reading in line for next subjectId
        if lstLine[0] ==  "Length,":
            RoadUserLength = lstLine[2] ## Extract length dimension for road user box
        if lstLine[0] ==  "Width,":
            RoadUserWidth = lstLine[2] ## Extract Width dimension for road user box
        if lstLine[0] ==  "Height,":
            RoadUserHeight = lstLine[2] ## Extract Height dimension for road user box
        if lstLine[0] ==  "Frames:":
            startFrame = int(lstLine[1][0:lstLine[1].find('-')]) ## get info on start frame
    elif len(lstLine) == 1: ## if line contains data points there are no blank space in it and thus not be splitted in lstLine
        subjectLineCount += 1
        digitLine = line.split(";")
        x = float(digitLine[0])+Xoffset     ## Extract X coordinate and add offset for georeferencing
        y = -(float(digitLine[1])-Yoffset)  ## Extract Y coordinate and add offset for georeferencing

        xpxl = digitLine[7]
        if xpxl == 'NoValue':
            xpxl=0.0
        else:
            xpxl = float(xpxl)+Xoffset

        ypxl = digitLine[8]
        if ypxl == 'NoValue':
            ypxl=0.0
        else:
            ypxl = -(float(ypxl)-Yoffset)

        ## Calculating the time stamp from video start time, framenumber and framerate:
        if subjectLineCount == 1:
            timesNudge = startFrame/500 ## startFrame is integer, so the result will be an integer. Calculate how many times the time nudge should be applied depending on the start frame number
            timeStamp = dateTime + deltaTime*startFrame + timesNudge*deltaTime/200 ## Number of frames into video since start + nudge the time lost due to the lack of precisoni of deltaTime on large startframenumbers
        elif subjectLineCount%500 == 0:
            timeStamp = timeStamp + deltaTime + deltaTime/200  ##  Nudge the time lost with deltaTime into place after the number of iterations as defined in the line above
        else:
            timeStamp = timeStamp + deltaTime ## Add one time step

        strTimeStamp = str(timeStamp).split(' ') ## Split timestamp in date part and time part
        splitTimeStamp = strTimeStamp[1].split('.') ## Split time part to extract milliseconds. If milliseconds are 0 then there is no split


        if not len(splitTimeStamp) == 1: ## only proceed with milliseconds rounding procedure if milliseconds are not 0
            dt2 = formatDateTime(strTimeStamp[0], strTimeStamp[1])
            if not dt2[5]+roundMilliSec(timeStamp)[0]>=60:
                newTimeStamp = datetime(dt2[0],dt2[1],dt2[2],dt2[3], dt2[4], (dt2[5]+roundMilliSec(timeStamp)[0]),roundMilliSec(timeStamp)[1]*1000) ## Add the rounded milliseocnds to the seconds (in case of round up) and the milliseconds place
            else:
                newTimeStamp = datetime(dt2[0],dt2[1],dt2[2],dt2[3], dt2[4]+1, 0, roundMilliSec(timeStamp)[1]*1000) ## In case of rounding to 60 sec add 1 minute and set seconds 0
        else:
            newTimeStamp = timeStamp

        ## Calculate framenumber
        frameNumber = startFrame + subjectLineCount-1

        ## write datapoint to frameDict
        if subjectId not in list(frameDict.keys()):
            frameDict[subjectId] = [trackPoint(x, y, newTimeStamp, frameNumber, str(subjectId), roadUserType, RoadUserLength, RoadUserWidth, RoadUserHeight, xpxl, ypxl)]
        else:
            frameDict[subjectId].append(trackPoint(x, y, newTimeStamp, frameNumber, str(subjectId), roadUserType, RoadUserLength, RoadUserWidth, RoadUserHeight, xpxl, ypxl, frameDict[subjectId][-1], backFrameLengthSec))

    line = inFile.readline()
    inLineCount += 1
    if inLineCount % 10000 == 0:
        print("Working on line number", inLineCount, "of", inFileName)

# Writing output .txt (CSV) files

## Writing headers
outFile.write(delim.join(["FrameID", "RespID", "X", "Y","DateTime","DeltaTimeSec"  "AkkuTimeSec" , \
               "StepBackTimeSec" , "DeltaDist", "AkkuDist"  , "StepBackDist" ,
             "Speed" , "AkkuAvgSpeedS" , "StepBackSpeed" , "StepBackDurationSec" , "Xpxl" ,
             "Ypxl"])+ "\n") # ",".join(["a","b","c"]) -> a,b,c

outFileBasic.write(delim.join(["FrameID" , "RespID" , "X" , "Y" , "DateTime"])+ "\n")


outStatFile.write(delim.join(["RespondentID" , "Distance" , "EuclidDist" , "Sinuosity" , \
                          "DurationSec" ,
                 "AvgSpeed" , "NumPoints" , "FromFrame" , "ToFrame", "RoadUserType" ,
                 "RoadUserLenght" , "RoadUSerWidth" , "RoadUserHeight"]) + "\n")

outLineCount = 1
subjectIds = list(frameDict.keys())
subjectIds.sort()
outStatLineCount = 1
## Writing aggregated stats for each track
for subjectId in subjectIds:
    pLast = frameDict[subjectId][-1] ## Last trackPoint
    pFirst = frameDict[subjectId][0]
    ## Calculate track sinuosity
    if dist2D(pFirst.x, pFirst.y, pLast.x, pLast.y) == 0:
        sinuosity = 999999999
    else:
        sinuosity = pLast.akkuDist/dist2D(pFirst.x, pFirst.y, pLast.x, pLast.y)

    outStatFile.write(delim.join([str(subjectId) , '%.2f' % (pLast.akkuDist) , '%.2f' % (dist2D(
        pFirst.x, pFirst.y, pLast.x, pLast.y)) , '%.4f' % sinuosity + delim
                     + '%.0f' % (pLast.akkuTimeSec) , '%.2f' % (pLast.akkuSpeed) + delim
                     + str(len(frameDict[subjectId])) , str(pFirst.frameId) + delim
                     + str(pLast.frameId) , pLast.userType , str(pLast.userTypeLength) ,
                                  str(pLast.userTypeWidth) , str(pLast.userTypeHeight)]) + "\n")
    outStatLineCount += 1
    ## Writing info for individual points
    ## Get min and max values for x, y , dateTime
    minX =  999999999
    maxX = -999999999
    minY =  999999999
    maxY = -999999999
    minDateTime = datetime.max
    maxDateTime = datetime.min
    for p in frameDict[subjectId]:
        outLineCount += 1
        if p.x > maxX: maxX = p.x
        if p.x < minX: minX = p.x
        if p.y > maxY: maxY = p.y
        if p.y < minY: minY = p.y
        if p.dateTime > maxDateTime: maxDateTime = p.dateTime
        if p.dateTime < minDateTime: minDateTime = p.dateTime
        outFile.write(delim.join([str(p.frameId) , str(subjectId) , '%.2f' % (p.x) , '%.2f' % (p.y) , ping + str(p.dateTime) + ping ,
                     '%.3f' % (p.deltaTimeSec) , '%.3f' % (p.akkuTimeSec) , '%.3f' % (p.stepBackTimeSec) ,
                     '%.2f' % (p.deltaDist), '%.2f' % (p.akkuDist) , '%.2f' % (p.stepBackDist) ,
                    '%.2f' % (p.speed) , '%.2f' % (p.akkuSpeed) , '%.2f' % (p.stepBackSpeed) ,
                    '%.2f' % (p.stepBackTimeSec) ,'%.2f' % (p.xpxl) , '%.2f' % (p.ypxl)]) + "\n")

        outFileBasic.write(delim.join([str(p.frameId) , str(subjectId) , '%.2f' % (p.x) ,
                                       '%.2f' % (p.y) , ping + str(p.dateTime) + ping]) + "\n")

# Closing files
inFile.close()
outFile.close()
outFileBasic.close()
outStatFile.close()

## Print messages
print("Tanalyst2CSV done")
print(str(inLineCount), "lines read from ", inFileName)
print(str(outLineCount), "lines written to ", outFileName)
print(str(outStatLineCount), "lines written to ", outStatFileName)
print("Outputs stored in " + path)
spendTime = wallClock()  - startExecusionTime
minutes = int(spendTime) / 60
seconds = spendTime % 60
print("Total execusion time:", int(minutes), "min", '%.2f' % seconds, "Sec")
# another way to print stuff which may be more convenient is the following:
print("Total execution time: {} min {0:.2f} sec".format(int(minutes), seconds))
