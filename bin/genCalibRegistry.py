#!/usr/bin/env python

import glob
import os
import re
import sqlite
import sys
import math
import datetime
import collections

import lsst.daf.base   as dafBase
import lsst.afw.image  as afwImage

import optparse

# Needs optparse w/ --create, etc. CPL
parser = optparse.OptionParser()
parser.add_option("--create", dest="create", default=False, action="store_true", 
                  help="Create new registry (clobber old)?")
parser.add_option("--root", dest="root", default=".", help="Root directory")
parser.add_option("--camera", dest="camera", default="hsc", help="Camera name: HSC|SC")
parser.add_option("--validity", type="int", dest="validity", default=30, help="Calibration validity (days)")
opts, args = parser.parse_args()

if len(args) > 0 or len(sys.argv) == 1:
    print "Unrecognised arguments:", sys.argv[1:]
    parser.print_help()
    sys.exit(1)

if opts.camera.lower() not in ("suprime-cam", "suprimecam", "sc", "hsc", "hscsim"):
    raise RuntimeError("Camera not recognised: %s" % camera)

registry = os.path.join(opts.root, "calibRegistry.sqlite3")

if os.path.exists(registry):
    os.unlink(registry)
conn = sqlite.connect(registry)

Row = collections.namedtuple("Row", ["calibDate", "mystery", "num", "ccd"])

for calib in ('bias', 'dark', 'flat', 'fringe'):
    cmd = "create table " + calib.lower() + " (id integer primary key autoincrement"
    cmd += ", validStart text, validEnd text"
    cmd += ", calibDate text, filter text, mystery text, num int, ccd int"
    cmd += ")"
    conn.execute(cmd)
    conn.commit()

    rowsPerFilter = dict()

    for fits in glob.glob(os.path.join(opts.root, calib.upper(), "20*-*-*", "?-?-*", "*",
                                       calib.upper() + "-*.fits*")):
        print fits
        if opts.camera.lower() in ("suprime-cam", "suprimecam", "sc"):
            m = re.search(r'\w+/(\d{4})-(\d{2})-(\d{2})/([A-Z]-[A-Z]-[A-Z0-9+]{1,4})/(\d+)/\w+-(\d{7})(\d).fits', fits)
        elif opts.camera.lower() in ("hsc", "hscsim"):
            m = re.search(r'\w+/(\d{4})-(\d{2})-(\d{2})/([A-Z]-[A-Z]-[A-Z0-9+]{1,4})/(\d+)/\w+-(\d{5})(\d{3}).fits', fits)
        if not m:
            print >>sys.stderr, "Warning: Unrecognized file:", fits
            continue
        year, month, day, filterName, mystery, num, ccd = m.groups()

        date = datetime.date(int(year), int(month), int(day))
        if filterName not in rowsPerFilter:
            rowsPerFilter[filterName] = list()
        rowsPerFilter[filterName].append(Row(date, mystery, num, ccd))


    # Fix up the validStart,validEnd so there are no overlaps
    for filterName, rows in rowsPerFilter.items():
        rows.sort(key=lambda row: row.calibDate)
        validity = datetime.timedelta(opts.validity)
        valids = collections.OrderedDict([(row.calibDate, [row.calibDate - validity,
                                                           row.calibDate + validity]) for row in rows])
        dates = valids.keys()
        numDates = len(dates)
        midpoints = [ t1 + (t2 - t1)//2 for t1, t2 in zip(dates[:numDates-1], dates[1:]) ]
        for i, (date, midpoint) in enumerate(zip(dates[:numDates-1], midpoints)):
            if valids[date][1] > midpoint:
                nextDate = dates[i+1]
                #print "Adjusting: %d %s --> %s : %s vs %s" % (i, date, nextDate, valids[date][1], midpoint)
                valids[nextDate][0] = midpoint
                valids[date][1] = midpoint
        del midpoints
        del dates

        for row in rows:
            calibDate = row.calibDate.isoformat()
            validStart = valids[row.calibDate][0].isoformat()
            validEnd = valids[row.calibDate][1].isoformat()

            # print "%f --> %f %f" % (calibDate, validStart, validEnd)

            conn.execute("INSERT INTO " + calib.lower() + " VALUES (NULL, ?, ?, ?, ?, ?, ?, ?)",
                         (validStart, validEnd, calibDate, filterName, row.mystery, row.num, row.ccd))
        

conn.commit()
conn.close()
