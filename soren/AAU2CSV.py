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
from common import * # the module with your functions
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





