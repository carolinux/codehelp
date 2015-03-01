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

# Settings
path = "C:\\Users\\lvp326\\Dropbox\\PhD\\Urban_Movement\\Code".replace("\\", "/")
fn = "00100002" ## Remember to set change videoData and videoStartTime below to match the current file
inFileName = fn + ".txt"
inFile = open(path + "/" + inFileName, "r")

outFileName = fn + "_out.txt"
outFile = open(path + "/" + outFileName, "w")

outFileNameBasic = fn + "_out_Basic.txt"
outFileBasic = open(path + "/" + outFileNameBasic, "w")

outStatFileName = fn + "_outStat.txt"
outStatFile = open(path + "/" + outStatFileName, "w")

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

## Defs
# Format date and time strings
def formatDateTime(dateStr, timeStr):
    listDate = dateStr.split("-")
    listTime = timeStr.split(":")
    listMilli = listTime[2].split(".")
    return int(listDate[0]), int(listDate[1]), int(listDate[2]), int(listTime[0]), int(listTime[1]), int(listMilli[0]), int(listMilli[1]) * 1000 ## * 1000 to get six digits on subseconds field

# Round MilliSec to 3 digits
def roundMilliSec(self): ## Cannot handle if milliseconds are 0 - the function should not be called if that is the case.
    tail = str(self)[-7:]
    split = str(round(float(tail), 3)).split('.')
    if len(split[1]) == 1:
        intSplit = [int(split[0]), int(split[1])*100] ## add two zeros to the end if the rounded millisecond number is only one digit
    else:
        intSplit = [int(split[0]), int(split[1])]
    return intSplit


# Calculate 2D distance
def dist2D(x1, y1, x2, y2):
    return(((x1 - x2) ** 2 + (y1 - y2) ** 2) ** 0.5)

## Classes
class trackPoint:
    def __init__(self, x, y, dateTimePass, frameId=0, Id=0, userType=None, userTypeLength=0, userTypeWidth=0, userTypeHeight=0, xpxl=None, ypxl=None, pPoint=None, stepsBackSec=None):

        # Definitions of parsed variables
        self.x = x
        self.y = y
        self.prevPoint = pPoint ## The entire trackPoint instance for the previous point.
        self.stepsBackSec = stepsBackSec
        self.frameId = frameId
        self.Id = Id
        self.dateTime = dateTimePass
        self.userType = userType
        self.userTypeLength = userTypeLength
        self.userTypeWidth = userTypeWidth
        self.userTypeHeight = userTypeHeight
        self.xpxl = xpxl
        self.ypxl = ypxl

        # Definitions of variables created inside trackPoint class
        ## Distance
        self.deltaDist = 0.0 ## Distance relative to the last location, m
        self.stepBackDist = 0.0  ## Distance relative to the point at a given point back in time, m
        self.akkuDist = 0.0  ## Distance relative to the start of the track, m

        ## Time
        self.deltaTimeSec = 0.0 ## Time spend relative to the last location, seconds
        self.stepBackTimeSec = 0.0  ## TODO: Time spend relative to a given point back in time, seconds
        self.akkuTimeSec = 0.0  ## Time spend relative to the start of the track, seconds

        ## Speed
        self.speed = 0.0     ## Speed relative to the last location, km/h
        self.stepBackSpeed = 0.0 ## TODO: Speed over the last second, km/h
        self.akkuSpeed = 0.0 ## Speed over entire track this far, km/h

        ## Azimuth
        self.angle = 0.0     ## From previous location (relative to the previous leg)
        self.stepBackAngle = 0.0 ## TODO: From location relative to a given point back in time (relative to the previous leg)
        self.akkuAngle = 0.0 ## From start of the track (relative to the end of the track)

        # Calculation of movement parameters for the track
        if pPoint: ## If the point is not the first of a track then calculate the following:
            self.deltaDist = dist2D(self.x, self.y, pPoint.x, pPoint.y)  ## Distance between points, in meters
            self.akkuDist = pPoint.akkuDist + self.deltaDist   ## Distance relative to the start of the track, in meters
            dtime = self.dateTime - self.prevPoint.dateTime
            self.deltaTimeSec = dtime.seconds + (dtime.microseconds / 1000000.0) ## Time spend relative to the last location, seconds
            self.akkuTimeSec = pPoint.akkuTimeSec + self.deltaTimeSec  ## Time spend relative to the start of the track, seconds
            if self.deltaTimeSec > 0:
                self.speed = (self.deltaDist / 1000) /(self.deltaTimeSec / 3600)     ## Speed relative to the last location, km/h
            else:
                self.speed = 0.0
            if self.akkuTimeSec > 0:
                self.akkuSpeed = (self.akkuDist / 1000) /(self.akkuTimeSec / 3600) ## Speed over entire track this far, km/h
            else:
                self.akkuSpeed = 0.0
            # --- Calculating parameters 'self.stepsBackSec' back in time --- Check if all below this line i trackpoint is correct!!!!! - Angles can be calculated in PostGIS using ST_Azimuth
            pp = self.prevPoint
            deltaT = 0.0 ##float((self.dateTime - pp.dateTime).seconds)
            c = 0
            while pp and deltaT < self.stepsBackSec:
                deltaT = (self.dateTime - pp.dateTime).seconds
##                if int(self.Id) in (0, 1) and int(self.frameId) in (61, 62):
##                    print(self.frameId, self.Id, pp.prevPoint.frameId, (self.dateTime - pp.dateTime).seconds, c, self.Id, deltaT)
                p = pp
                pp = pp.prevPoint
                ##print(pp.Id, deltaT, pp.dateTime)
                c += 1
            if not pp:
                self.stepBackDist = 0.0
                self.stepBackTimeSec = 0.0
                self.stepBackAngle = 0.0
            else:
                ##print(deltaT, self.stepsBackSec, self.akkuDist, pp.akkuDist)
                self.stepBackDist = self.akkuDist - pp.akkuDist
                self.stepBackTimeSec = (self.dateTime - pp.dateTime).seconds
                ##print(self.dateTime, pp.dateTime, self.stepBackTimeSec)
##                self.stepBackSpeed = (self.stepBackDist / 1000) /(self.stepBackTimeSec / 3600) ## TODO ------------------ problem with division with zero!
                self.stepBackAngle = 0.0 ##TODO
##            if int(self.frameId) in (61, 62, 63):
##                print(c, pp, self.frameId, self.dateTime, deltaT, '%.2f' % self.stepBackDist, '%.2f' % self.stepBackSpeed)
              # end of  questionable section

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
outFile.write("FrameID" + delim + "RespID" + delim + "X" + delim + "Y" + delim + "DateTime" + delim +
             "DeltaTimeSec" + delim + "AkkuTimeSec" + delim + "StepBackTimeSec" + delim +
             "DeltaDist"+ delim + "AkkuDist"  + delim + "StepBackDist" + delim +
             "Speed" + delim + "AkkuAvgSpeedS" + delim + "StepBackSpeed" + delim + "StepBackDurationSec" + delim + "Xpxl" + delim + "Ypxl" + "\n")

outFileBasic.write("FrameID" + delim + "RespID" + delim + "X" + delim + "Y" + delim + "DateTime" + "\n")


outStatFile.write("RespondentID" + delim + "Distance" + delim + "EuclidDist" + delim + "Sinuosity" + delim + "DurationSec" + delim +
                 "AvgSpeed" + delim + "NumPoints" + delim + "FromFrame" + delim + "ToFrame"+ delim + "RoadUserType" + delim + "RoadUserLenght" + delim + "RoadUSerWidth" + delim + "RoadUserHeight" + "\n")

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

    outStatFile.write(str(subjectId) + delim + '%.2f' % (pLast.akkuDist) + delim + '%.2f' % (dist2D(pFirst.x, pFirst.y, pLast.x, pLast.y)) + delim + '%.4f' % sinuosity + delim
                     + '%.0f' % (pLast.akkuTimeSec) + delim + '%.2f' % (pLast.akkuSpeed) + delim
                     + str(len(frameDict[subjectId])) + delim + str(pFirst.frameId) + delim
                     + str(pLast.frameId) + delim + pLast.userType + delim + str(pLast.userTypeLength) + delim + str(pLast.userTypeWidth) + delim + str(pLast.userTypeHeight) + "\n")
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
        outFile.write(str(p.frameId) + delim + str(subjectId) + delim + '%.2f' % (p.x) + delim + '%.2f' % (p.y) + delim + ping + str(p.dateTime) + ping + delim +
                     '%.3f' % (p.deltaTimeSec) + delim + '%.3f' % (p.akkuTimeSec) + delim + '%.3f' % (p.stepBackTimeSec) + delim +
                     '%.2f' % (p.deltaDist)+ delim + '%.2f' % (p.akkuDist) + delim + '%.2f' % (p.stepBackDist) + delim +
                    '%.2f' % (p.speed) + delim + '%.2f' % (p.akkuSpeed) + delim + '%.2f' % (p.stepBackSpeed) + delim + '%.2f' % (p.stepBackTimeSec) + delim +'%.2f' % (p.xpxl) + delim + '%.2f' % (p.ypxl) + "\n")

        outFileBasic.write(str(p.frameId) + delim + str(subjectId) + delim + '%.2f' % (p.x) + delim + '%.2f' % (p.y) + delim + ping + str(p.dateTime) + ping + "\n")

# Closing files
inFile.close()
outFile.close()
outFileBasic.close()
outStatFile.close()

## Print messages
print("Tanalyst2CSV done")
print(str(inLineCount), "lines read from", inFileName)
print(str(outLineCount), "lines written to", outFileName)
print(str(outStatLineCount), "lines written to", outStatFileName)
print("Outputs stored in " + path)
spendTime = wallClock()  - startExecusionTime
minutes = int(spendTime) / 60
seconds = spendTime % 60
print("Total execusion time:", int(minutes), "min", '%.2f' % seconds, "Sec")
