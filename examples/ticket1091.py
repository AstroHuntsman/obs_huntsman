import pylab as plt

import lsst.pex.logging as pexLog
import lsst.afw.table as afwTable
import lsst.meas.algorithms as measAlg

from utils import *

def addToParser(parser):
    if parser is None:
        from optparse import OptionParser
        parser = OptionParser()
    parser.add_option('--force', '-f', '--force-deblend', dest='force',
                      action='store_true', default=False, help='Force re-running the deblender?')
    parser.add_option('--force-det', '--force-detect', '--force-detection', '-d',
                      dest='forcedet', action='store_true', default=False,
                      help='Force re-running the detection stage?')
    parser.add_option('--force-calib', dest='forcecalib', action='store_true', default=False,
                      help='Force re-running the Calibration stage?')
    parser.add_option('--force-isr', dest='forceisr', action='store_true', default=False,
                      help='Force re-running the ISR stage?')
    parser.add_option('-s', '--sources', dest='sourcefn', default=None,
                      help='Output filename for source table (FITS)')
    parser.add_option('-H', '--heavy', dest='heavypat', default=None, 
                      help='Output filename pattern for heavy footprints (with %i pattern); FITS.  "yes" for heavy-VVVV-CC-IDID.fits')
    parser.add_option('--nkeep', '-n', dest='nkeep', default=0, type=int,
                      help='Cut to the first N deblend families')
    parser.add_option('--drill', '-D', dest='drill', action='append', type=int, default=[],
                      help='Drill down on individual source IDs')
    parser.add_option('--no-deblend-plots', dest='deblendplots', action='store_false', default=True,
                      help='Do not make deblend plots')
    parser.add_option('--no-measure-plots', dest='measplots', action='store_false', default=True,
                      help='Do not make measurement plots')
    parser.add_option('--no-after-plots', dest='noafterplots', action='store_true',
                      help='Do not make post-deblend+measure plots')
    parser.add_option('--no-plots', dest='noplots', action='store_true', help='No plots at all; --no-deblend-plots, --no-measure-plots, --no-after-plots')
    parser.add_option('--threads', dest='threads', type=int, help='Multiprocessing for plots?')
    parser.add_option('--overview', dest='overview', help='Produce an overview plot?')

    #parser.add_option('--drop-psfs', dest='drop_psf', help='Drop deblends 

    parser.add_option('-v', dest='verbose', action='store_true')

class DebugDeblendTask(measAlg.SourceDeblendTask):
    def __init__(self, *args, **kwargs):
        self.prefix = kwargs.pop('prefix', '')
        self.drill = kwargs.pop('drill', [])
        if not len(self.drill):
            self.drill = None
        self.plotnum = 0
        super(DebugDeblendTask, self).__init__(*args, **kwargs)

    def run(self, exposure, sources, psf):
        if self.drill:
            keep = afwTable.SourceCatalog(sources.getTable())
            for src in sources:
                if src.getId() in self.drill:
                    keep.append(src)
            keep.sort()
            sources = keep
        self.deblend(exposure, sources, psf)

    def savefig(self, fn):
        plotfn = '%s%s.png' % (self.prefix, fn)
        plt.savefig(plotfn)
        print 'wrote', plotfn

    def preSingleDeblendHook(self, exposure, srcs, i, fp, psf, psf_fwhm, sigma1):
        mi = exposure.getMaskedImage()
        parent = srcs[i]
        pid = parent.getId()
        plt.clf()
        fp = parent.getFootprint()
        pext = getExtent(fp.getBBox())
        imargs = dict(interpolation='nearest', origin='lower')
        pim = footprintToImage(parent.getFootprint(), mi).getArray()
        plt.imshow(pim, extent=pext, **imargs)
        plt.gray()
        plt.title('parent %i' % pid)
        pks = fp.getPeaks()
        plt.plot([pk.getIx() for pk in pks], [pk.getIy() for pk in pks], 'rx')
        plt.axis(pext)
        self.savefig('%04i-pim' % self.plotnum)

        plt.clf()
        mask = mi.getMask()
        mim = mask.getArray()
        bitmask = mask.getPlaneBitMask('DETECTED')
        plt.imshow((mim & bitmask) > 0, **imargs)
        plt.gray()
        plt.title('parent %i DET' % pid)
        pks = fp.getPeaks()
        plt.plot([pk.getIx() for pk in pks], [pk.getIy() for pk in pks], 'rx')
        plt.axis(pext)
        self.savefig('%04i-pmask' % self.plotnum)

    def postSingleDeblendHook(self, exposure, srcs, i, npre, kids, fp, psf, psf_fwhm, sigma1, res):
        mi = exposure.getMaskedImage()
        parent = srcs[i]
        plotDeblendFamily(mi, parent, kids, srcs, sigma1, ellipses=False)
        self.savefig('%04i-posta' % self.plotnum)
        plotDeblendFamily(mi, parent, kids, srcs, sigma1, plotb=True, ellipses=False)
        self.savefig('%04i-postb' % self.plotnum)
        self.plotnum += 1


def runDeblend(dataRef, sourcefn, conf, procclass, forceisr=False, forcecalib=False, forcedet=False,
               verbose=False, drill=[], debugDeblend=True, debugMeas=True,
               calibInput='postISRCCD', tweak_config=None):
    dr = dataRef
    mapper = datarefToMapper(dr)

    conf.calibrate.doComputeApCorr = False
    conf.calibrate.doAstrometry = False
    conf.calibrate.doPhotoCal = False
    conf.calibrate.measurement.doApplyApCorr = False
    conf.measurement.doApplyApCorr = False

    conf.validate()

    # Only do ISR, Calibration, and Detection if necessary (or forced)
    doIsr    = False
    doCalib  = False
    doDetect = False
    print 'Looking for calexp', mapper.map('calexp', dr.dataId)
    print 'Looking for psf', mapper.map('psf', dr.dataId)
    print 'Looking for src', mapper.map('src', dr.dataId)
    try:
        psf = dr.get('psf')
        print 'PSF:', psf
    except:
        print 'No PSF'
        doCalib = True
    try:
        expo = dr.get('calexp')
        print 'Calexp:', expo
    except:
        print 'No calexp'
        doCalib = True
    try:
        srcs = dr.get('src')
        print 'Srcs', srcs
    except:
        print 'No sources'
        doDetect = True
        srcs = None

    if doCalib:
        print 'Looking for', calibInput
        try:
            calin = dr.get(calibInput)
            print calibInput, calin
        except:
            print 'No', calibInput
            doIsr = True

    if forceisr:
        print 'Forcing ISR'
        doIsr = True
    if forcecalib:
        print 'Forcing calibration'
        doCalib = True
    if forcedet:
        print 'Forcing detection'
        doDetect = True
        srcs = None

    conf.doIsr            = doIsr
    conf.doCalibrate      = doCalib
    conf.doWriteCalibrate = doCalib
    conf.doDetection      = doDetect

    if tweak_config:
        tweak_config(conf)

    if not doDetect:
        # Massage the sources into a pre-deblended state.
        print 'Got', len(srcs), 'sources'
        # Remove children from the Catalog (don't re-deblend)
        n0 = len(srcs)
        i=0
        while i < len(srcs):
            if srcs[i].getParent():
                del srcs[i]
            else:
                i += 1
        n1 = len(srcs)
        if n1 != n0:
            print "Dropped %i of %i 'child' sources (%i remaining)" % ((n0-n1), n0, n1)
        # Make sure the IdFactory exists and doesn't duplicate IDs
        # (until JimB finishes #2083)
        f = srcs.getTable().getIdFactory()
        if f is None:
            f = afwTable.IdFactory.makeSimple()
            srcs.getTable().setIdFactory(f)
        maxid = max([src.getId() for src in srcs])
        f.notify(maxid)
        print 'Max ID in catalog:', maxid

        # still set conf.doDetection = True here so the schema gets populated properly...
        conf.doDetection = True

    conf.doDeblend = True
    conf.doMeasurement = True
    conf.doWriteSources = True
    conf.doWriteHeavyFootprintsInSources = True
    conf.measurement.doRemoveOtherSources = True

    if debugDeblend:
        conf.doDeblend = False
        # We have to add the schema elements in the right order...
        conf.doMeasurement = False
    if debugMeas:
        conf.doMeasurement = False

    proc = procclass(config=conf, name='ProcessCcd')
    if verbose:
        proc.log.setThreshold(pexLog.Log.DEBUG)

    if debugDeblend:
        log = None
        if verbose:
            log = pexLog.Log(proc.log, 'deblend')
            log.setThreshold(pexLog.Log.DEBUG)
        proc.deblend = DebugDeblendTask(proc.schema, config=conf.deblend, log=log,
                                        prefix = 'deblend-', drill=drill)
        conf.doDeblend = True
        if not debugMeas:
            # Put in the normal measurement subtask; we have to do
            # this after the deblending task to ensure the schema
            # elements get added in the right order.
            proc.measurement = measAlg.SourceMeasurementTask(proc.schema,
                                                             algMetadata=proc.algMetadata,
                                                             config=conf.measurement)
            conf.doMeasurement = True

    if debugMeas:
        log = None
        if verbose:
            log = pexLog.Log(proc.log, 'measurement')
            log.setThreshold(pexLog.Log.DEBUG)
        proc.measurement = DebugSourceMeasTask(proc.schema, algMetadata=proc.algMetadata,
                                               config=conf.measurement, log=log,
                                               plotmasks = False, prefix = 'measure-')
        conf.doMeasurement = True

    if srcs:
        assert(proc.schema == srcs.getSchema())

    conf.doDetection = doDetect
    res = proc.run(dr, sources=srcs)

    if srcs:
        assert(proc.schema == srcs.getSchema())
        assert(srcs.getSchema() == res.sources.getSchema())
    assert(proc.schema == res.sources.getSchema())
    srcs = res.sources

    print 'Processing finished; srcs should have been written to:'
    print '  ', mapper.map('src', dr.dataId)

    return srcs



# for multiprocess.Pool.map()
def _plotfunc((args, kwargs, fn)):
    plotDeblendFamilyReal(*args, **kwargs)
    plt.savefig(fn)
    print 'saved', fn

def t1091main(dr, opt, conf, proc, patargs={}, rundeblendargs={}, pool=None):
    if opt.noplots:
        opt.deblendplots = False
        opt.measplots = False
        opt.noafterplots = True
    
    cat = None
    if not opt.force:
        cat = readCatalog(opt.sourcefn, opt.heavypat, ndeblends=opt.nkeep, dataref=dr,
                          patargs=patargs)
    if cat is None:
        cat = runDeblend(dr, opt.sourcefn, conf, proc,
                         opt.forceisr, opt.forcecalib, opt.forcedet,
                         opt.verbose, opt.drill, opt.deblendplots, opt.measplots,
                         **rundeblendargs)

        if opt.sourcefn:
            print 'Writing FITS to', opt.sourcefn
            cat.writeFits(opt.sourcefn)

        # Write heavy footprints
        if opt.heavypat is not None:
            for src in cat:
                if not src.getParent():
                    continue
                k = src.getId()
                mim = footprintToImage(src.getFootprint())
                args = patargs.copy()
                args.update(id=k)
                fn = opt.heavypat % args
                mim.writeFits(fn)
                print 'Wrote', fn

    if opt.overview is not None:
        exposure = dr.get('calexp')
        print 'Exposure', exposure
        mi = exposure.getMaskedImage()
        sigma1 = get_sigma1(mi)
        W,H = mi.getWidth(), mi.getHeight()
        im = mi.getImage().getArray()
        dpi=100
        plt.figure(figsize=(1+W/dpi, 1+H/dpi), dpi=dpi)
        plt.clf()
        plt.imshow(im, interpolation='nearest', origin='lower', vmin=-2.*sigma1, vmax=10.*sigma1)
        ax = plt.axis()
        plt.gray()
        for src in cat:
            #fp = src.getFootprint()
            #bb = fp.getBBox()
            ext = getExtent(src.getFootprint().getBBox())
            xx = [ext[0],ext[1],ext[1],ext[0],ext[0]]
            yy = [ext[2],ext[2],ext[3],ext[3],ext[2]]
            if len(src.getFootprint().getPeaks()) == 1:
                c = 'r'
            else:
                c = 'y'
            plt.plot(xx, yy, '-', color=c)
        plt.axis(ax)
        plt.savefig(opt.overview)
        
    if opt.nkeep:
        cat = cutCatalog(cat, opt.nkeep)

    if opt.noafterplots:
        return

    but = datarefToButler(dr)
    idbits = but.get('ccdExposureId_bits')
    idmask = (1 << idbits)-1
    
    exposure = dr.get('calexp')
    print 'Exposure', exposure
    mi = exposure.getMaskedImage()
    sigma1 = get_sigma1(mi)
    fams = getFamilies(cat)

    A = []
    for j,(parent,children) in enumerate(fams):
        args = (mi, parent, children, cat, sigma1)
        fn1 = 'deblend-%04i-a.png' % j
        kwargs1 = dict(ellipses=True, idmask=idmask)
        fn2 = 'deblend-%04i-b.png' % j
        kwargs2 = dict(ellipses=True, plotb=True, idmask=idmask)

        if pool is None:
            plotDeblendFamily(*args, **kwargs1)
            plt.savefig(fn1)
            print 'saved', fn1
            plotDeblendFamily(*args, **kwargs2)
            plt.savefig(fn2)
            print 'saved', fn2

        else:
            A.append((plotDeblendFamilyPre(*args, **kwargs1), kwargs1, fn1))
            A.append((plotDeblendFamilyPre(*args, **kwargs2), kwargs2, fn2))

    if pool:
        pool.map(_plotfunc, A)
