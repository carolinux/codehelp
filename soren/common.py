from datetime import datetime
## Defs
# Format date and time strings
def formatDateTime(dateStr, timeStr):
    dateTimeStr = dateStr +" "+timeStr
    dt = datetime.strptime(dateTimeStr, "%Y-%m-%d %H:%S:%M.%f") # this turns a string into a
    # datetime object according to a format
    return dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second, dt.microsecond

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
# moved this to a common module so that we don't duplicate it in the files
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

