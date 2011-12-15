#!/usr/bin/env python

import os

import unittest
import lsst.utils.tests as utilsTests

from lsst.pex.policy import Policy
import lsst.daf.persistence as dafPersist
from lsst.obs.suprimecam import SuprimecamMapper

import lsst.afw.display.ds9 as ds9
import lsst.afw.display.utils as displayUtils

import lsst.afw.geom as afwGeom
import lsst.afw.cameraGeom as cameraGeom
import lsst.afw.cameraGeom.utils as cameraGeomUtils
try:
    type(display)
except NameError:
    display = False


def getButler(datadir):
    bf = dafPersist.ButlerFactory(mapper=SuprimecamMapper(root=os.path.join(datadir, "hsc")))
    return bf.create()


class GetRawTestCase(unittest.TestCase):
    """Testing butler raw image retrieval"""

    def setUp(self):
        self.datadir = os.getenv("TESTDATA_SUBARU_DIR")
        self.expId = 204
        self.ccdList = (0, 100)
        self.untrimmedSize = (2272, 4273)
        self.trimmedSize = (2048, 4096)
        self.ampBox = afwGeom.Box2I(afwGeom.Point2I(0, 0), afwGeom.ExtentI(512, 2048))

        assert self.datadir, "testdata_subaru is not setup"

    def testRaw(self):
        """Test retrieval of raw image"""

        frame = 0
        for ccdNum in self.ccdList:
            butler = getButler(self.datadir)
            raw = butler.get("raw", visit=self.expId, ccd=ccdNum)
            ccd = raw.getDetector()

            print "Visit: ", expId
            print "width: ",              raw.getWidth()
            print "height: ",             raw.getHeight()
            print "detector(amp) name: ", ccd.getId().getName()

            self.assertEqual(raw.getWidth(), self.untrimmedSize[0])
            self.assertEqual(raw.getHeight(), self.untrimmedSize[1])
            self.assertEqual(raw.getFilter().getFilterProperty().getName(), "i") 
            self.assertEqual(ccd.getId().getName(), "%03d" % ccdNum)

            trimmed = ccd.getAllPixels(True).getDimensions()
            self.assertEqual(trimmed.getWidth(), self.trimmedSize[0])
            self.assertEqual(trimmed.getHeight(), self.trimmedSize[1])

            for amp in ccd:
                amp = cameraGeom.cast_Amp(amp)
                self.assertEqual(amp.getDataSec(True), self.ampBox)

            if display:
                ccd = cameraGeom.cast_Ccd(raw.getDetector())
                for amp in ccd:
                    amp = cameraGeom.cast_Amp(amp)
                    print ccd.getId(), amp.getId(), amp.getDataSec().toString(), \
                          amp.getBiasSec().toString(), amp.getElectronicParams().getGain()
                cameraGeomUtils.showCcd(ccd, ccdImage=raw, frame=frame)
                frame += 1


#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-

def suite():
    """Returns a suite containing all the test cases in this module."""

    utilsTests.init()

    suites = []
    suites += unittest.makeSuite(GetRawTestCase)
    suites += unittest.makeSuite(utilsTests.MemoryTestCase)
    return unittest.TestSuite(suites)

def run(shouldExit = False):
    """Run the tests"""
    utilsTests.run(suite(), shouldExit)

if __name__ == "__main__":
    run(True)
