#-------------------------------------------------------------------------------
# Name:        AAU2PostGIS
# Purpose:     Converts trajectory data from AAU Computer Vision software output to a CSV file to enable import to PostGIS
#
# Authors:     Soren Zebitz Nielsen, szn@ign.ku.dk, Hans Skov-Petersen, hsp@ign.ku.dk
#
# Created:     05-02-2015
# Copyright:   (c) Soren Zebitz Nielsen 2015
#
# Note:        There is a rounding bug for milliseconds in that it both can yield  .x66000 and .x67000 and the error is unsystematic
#              The solution to that problem is to run a simple search and replace for either 66000' or 67000' in the output .txt (CSV) file depending on which rounding format is preferred.
#-------------------------------------------------------------------------------

## Imports
from datetime import datetime ,timedelta
from time import time as wallClock
from sys import exit

## Settings
path = "C:\\Users\\lvp326\\Dropbox\\PhD\\Urban_Movement\\Code".replace("\\", "/")
fn = "output-6-14-11-30-NY"
inFileName = fn + ".txt"
inHdl = open(path + "/" + inFileName, "r")

outFileName = fn + "_out.txt"
outHdl = open(path + "/" + outFileName, "w")

outFileNameBasic = fn + "_out_Basic.txt"
outHdlBasic = open(path + "/" + outFileNameBasic, "w")

outStatFileName = fn + "_outStat.txt"
outStatHdl = open(path + "/" + outStatFileName, "w")

frameFlagId = "Framenumber:"
subjectFlagId = "ID"
frameLineFilter = 1 ## Only every 1/frameLineFilter trackline will be processed
startExecusionTime = wallClock()
backFrameLengthSec = 5

frameDict = {}
delim = ";"
ping = "'"

## Classes

class trackPoint:
    def __init__(self, x, y, date, time, frameId=0, Id=0, pPoint=None, stepsBackSec=None):
        self.x = x
        self.y = y
        self.prevPoint = pPoint
        self.stepsBackSec = stepsBackSec
        self.frameId = frameId
        self.Id = Id
        dt = formatDateTime(date, time)
        try:
            self.dateTime = datetime(dt[2], dt[1], dt[0], dt[3], dt[4], dt[5], dt[6])
        except:
            print("Datetime must be given as MM-DD-YYYY HH:MM:SS:MS")
            print("12-06-2013 14:00:00:100")
            print("Parameters given:", dt[0], dt[1], dt[2], dt[3], dt[4], dt[5], dt[6])
            ##exit(0)
        self.deltaDist = 0.0 ## Distance relative to the last location, m
        self.stepBackDist = 0.0  ## Distance relative to the at a given point back in time, m
        self.akkuDist = 0.0  ## Distance relative to the start of the track, m

        self.deltaTimeSec = 0.0 ## Time spend relative to the last location, seconds
        self.stepBackTimeSec = 0.0  ## TODO: Time spend relative to a given point back in time, seconds
        self.akkuTimeSec = 0.0  ## Time spend relative to the start of the track, seconds

        self.speed = 0.0     ## Speed relative to the last location, km/h
        self.stepBackSpeed = 0.0 ## TODO: Speed over the last second, km/h
        self.akkuSpeed = 0.0 ## Speed over entire track this far, km/h

        self.angle = 0.0     ## From previous location (relative to the previous leg)
        self.stepBackAngle = 0.0 ## TODO: From location relative to a given point back in time (relative to the previous leg)
        self.akkuAngle = 0.0 ## From start of the track (relative to the end of the track)
        if pPoint:
            self.deltaDist = dist2D(self.x, self.y, pPoint.x, pPoint.y)  ## m
            self.akkuDist = pPoint.akkuDist + self.deltaDist   ## Distance relative to the start of the track, m
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
            ## --- Calculating parameters 'self.stepsBackSec' back in time ---
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
                ##self.stepBackSpeed = (self.stepBackDist / 1000) /(self.stepBackTimeSec / 3600) ## TODO
                self.stepBackAngle = 0.0 ##TODO
##            if int(self.frameId) in (61, 62, 63):
##                print(c, pp, self.frameId, self.dateTime, deltaT, '%.2f' % self.stepBackDist, '%.2f' % self.stepBackSpeed)

# Format date and time strings
def formatDateTime(dateStr, timeStr):
    ## Should be operated by datetime.strftime(), but it doesn't seems to work on microseconds
    listDate = dateStr.split("-")
    listTime = timeStr.split(":")
    ## return: year, month, day, hour, min, sec, millisec
    return int(listDate[0]), int(listDate[1]), int(listDate[2]), int(listTime[0]), int(listTime[1]), int(listTime[2]), int(listTime[3]) * 1000

def dist2D(x1, y1, x2, y2):
    return(((x1 - x2) ** 2 + (y1 - y2) ** 2) ** 0.5)

## Main
line = inHdl.readline()
inLineCount = 0
frameLineCount = 1
while line:
    lstLine = line.split(" ")
    if lstLine[0] == frameFlagId:
        if len(frameDict) >= 1:
            subjectIds = list(frameDict.keys())
            subjectIds.sort()
        frameNumber = lstLine[1]
        date = lstLine[3]
        time = lstLine[4].strip(";\n")
    if lstLine[0] == subjectFlagId:
        if frameLineCount % frameLineFilter == 0:
            subjectId = int(lstLine[1][:-1].strip(";\n"))
            x = lstLine[3].replace(",", ".").strip(";\n")
            y = lstLine[2].replace(",", ".").strip(";\n")
            if subjectId not in list(frameDict.keys()):
                frameDict[subjectId] = [trackPoint(float(x), float(y), date, time, frameNumber, str(subjectId))]
            else:
                frameDict[subjectId].append(trackPoint(float(x), float(y), date, time, frameNumber, str(subjectId), frameDict[subjectId][-1], backFrameLengthSec))
        frameLineCount += 1
    line = inHdl.readline()
    inLineCount += 1
    if inLineCount % 10000 == 0:
        print("Working on line number", inLineCount, "of", inFileName)

## Writing headers
outHdl.write("FrameID" + delim + "RespID" + delim + "X" + delim + "Y" + delim + "DateTime" + delim +
             "DeltaTimeSec" + delim + "AkkuTimeSec" + delim + "StepBackTimeSec" + delim +
             "DeltaDist"+ delim + "AkkuDist"  + delim + "StepBackDist" + delim +
             "Speed" + delim + "AkkuAvgSpeedS" + delim + "StepBackSpeed" + delim + "StepBackDurationSec" + "\n")

outStatHdl.write("RespondentID" + delim + "Distance" + delim + "EuclidDist" + delim + "Sinuosity" + delim + "DurationMin" + delim +
                 "AvgSpeed" + delim + "NumPoints" + delim + "FromFrame" + delim + "ToFrame"+ "\n")

outHdlBasic.write("FrameID" + delim + "RespID" + delim + "X" + delim + "Y" + delim + "DateTime" + "\n")

outLineCount = 1
subjectIds = list(frameDict.keys())
subjectIds.sort()
outStatLineCount = 1
for subjectId in subjectIds:
    ## Writing aggregated stats for each track
    pLast = frameDict[subjectId][-1] ## Last trackPoint
    pFirst = frameDict[subjectId][0]
     ## Calculate track sinuosity
    if dist2D(pFirst.x, pFirst.y, pLast.x, pLast.y) == 0:
        sinuosity = 999999999
    else:
        sinuosity = pLast.akkuDist/dist2D(pFirst.x, pFirst.y, pLast.x, pLast.y)

    outStatHdl.write(str(subjectId) + delim + '%.2f' % (pLast.akkuDist) + delim + '%.2f' % (dist2D(pFirst.x, pFirst.y, pLast.x, pLast.y)) + delim + '%.4f' % sinuosity + delim
                     + '%.2f' % (pLast.akkuTimeSec / 60) + delim + '%.2f' % (pLast.akkuSpeed) + delim
                     + str(len(frameDict[subjectId])) + delim + str(frameDict[subjectId][0].frameId) + delim
                     + str(pLast.frameId) + "\n")
    outStatLineCount += 1
    ## Writing info for individual points
    for p in frameDict[subjectId]:
        outLineCount += 1
        ##print(type((p.frameId)), type(p.deltaTime), type(p.deltaDist), type(p.stepBackDist), type(p.speed), type(p.akkuSpeed), type(p.stepBackSpeed))
        outHdl.write(p.frameId + delim + str(subjectId) + delim + '%.2f' % (p.x) + delim + '%.2f' % (p.y) + delim + ping + str(p.dateTime) + ping + delim +
                     '%.3f' % (p.deltaTimeSec) + delim + '%.3f' % (p.akkuTimeSec) + delim + '%.3f' % (p.stepBackTimeSec) + delim +
                     '%.2f' % (p.deltaDist)+ delim + '%.2f' % (p.akkuDist) + delim + '%.2f' % (p.stepBackDist) + delim +
                     '%.2f' % (p.speed) + delim + '%.2f' % (p.akkuSpeed) + delim + '%.2f' % (p.stepBackSpeed) + delim + str(backFrameLengthSec) + "\n")
        outHdlBasic.write(p.frameId + delim + str(subjectId) + delim + '%.2f' % (p.x) + delim + '%.2f' % (p.y) + delim + ping + str(p.dateTime) + ping + "\n")

inHdl.close()
outHdl.close()
outHdlBasic.close()
outStatHdl.close()

print("AAU2CSV done...")
print(str(inLineCount), "lines read from", inFileName)
print(str(outLineCount), "lines written to", outFileName)
print(str(outStatLineCount), "lines written to", outStatFileName)
spendTime = wallClock()  - startExecusionTime
minutes = int(spendTime) / 60
seconds = spendTime % 60
print("Total execusion time:", int(minutes), "min", '%.2f' % seconds, "Sec")





