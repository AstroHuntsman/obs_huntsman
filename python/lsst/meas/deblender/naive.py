import math

import lsst.afw.image as afwImage
import lsst.afw.geom  as afwGeom
import lsst.afw.math  as afwMath

def deblend(footprints, peaks, maskedImage, psf, psffwhm):
    print 'Naive deblender starting'
    print 'footprints', footprints
    print 'maskedImage', maskedImage
    print 'psf', psf
    allt = []
    allp = []
    allbgsub = []
    allmod = []
    allmod2 = []
    
    img = maskedImage.getImage()
    for fp,pks in zip(footprints,peaks):
        bb = fp.getBBox()
        W,H = bb.getWidth(), bb.getHeight()
        x0,y0 = bb.getMinX(), bb.getMinY()

        templs = []
        bgsubs = []
        models = []
        models2 = []
        #for pk in fp.getPeaks():
        print 'Footprint x0,y0', x0,y0
        print 'W,H', W,H
        for pk in pks:
            template = afwImage.MaskedImageF(W,H)
            template.setXY0(x0,y0)
            cx,cy = pk.getIx(), pk.getIy()
            timg = template.getImage()
            p = img.get(cx,cy)
            timg.set(cx - x0, cy - y0, p)
            #template.set(cx,cy, 
            for dy in range(H-(cy-y0)):
                #print 'dy', dy
                for dx in range(-(cx-x0), W-(cx-x0)):
                    #print 'dx', dx
                    if dy == 0 and dx == 0:
                        continue
                    # twofold rotational symmetry
                    xa,ya = cx+dx, cy+dy
                    xb,yb = cx-dx, cy-dy
                    #print 'xa,ya', xa,ya
                    if not fp.contains(afwGeom.Point2I(xa, ya)):
                        #print ' (oob)'
                        continue
                    #print 'xb,yb', xb,yb
                    if not fp.contains(afwGeom.Point2I(xb, yb)):
                        #print ' (oob)'
                        continue
                    pa = img.get(xa, ya)
                    pb = img.get(xb, yb)
                    #print 'pa', pa, 'pb', pb
                    mn = min(pa,pb)
                    # Monotonic?
                    timg.set(xa - x0, ya - y0, mn)
                    timg.set(xb - x0, yb - y0, mn)
            templs.append(timg)

        # Now try fitting a PSF + smooth background model to the template.
        # Smooth background = ....?
        # ... median filter?
        # ... from our friends down at math::makeBackground?

        # ... constant, linear, (quadratic?) terms with least-squares fit?

        # ... implicitly computed by measuring flux in annuli or symmetrically-averaged sectors (clever RHL)

        # The SDSS deblender evaluates this model in a set of annuli --
        #     fp->deblend_psf_nann = 3;   in SDSSDeblender.cc
        #     -> * min(1, fp->frame[c].psf->width


        #for timg in templs:
        for pk in pks:
            if True:
                print 'PSF FWHM', psffwhm
                R0 = int(math.ceil(psffwhm * 2.))
                R1 = int(math.ceil(psffwhm * 3.))
                print 'R0', R0, 'R1', R1
                S = 2 * R1
                print 'S = ', S

                cx,cy = pk.getFx(), pk.getFy()
                #icx,icy = pk.getIx(), pk.getIy()
                psfimg = psf.computeImage(afwGeom.Point2D(pk.getFx(), pk.getFy()),
                                          afwGeom.Extent2I(S, S))
                bbox = psfimg.getBBox(afwImage.PARENT)
                print 'PSF bbox X:', bbox.getMinX(), bbox.getMaxX()
                print 'PSF bbox Y:', bbox.getMinY(), bbox.getMaxY()
                bbox.clip(fp.getBBox())
                print 'clipped bbox X:', bbox.getMinX(), bbox.getMaxX()
                print 'clipped bbox Y:', bbox.getMinY(), bbox.getMaxY()
                px0,py0 = psfimg.getX0(), psfimg.getY0()

                xlo,xhi = bbox.getMinX(),bbox.getMaxX()
                ylo,yhi = bbox.getMinY(),bbox.getMaxY()

                import numpy as np
                #import np.linalg

                # Number of terms -- PSF, constant, X, Y
                NT = 4
                NT2 = 7
                # Number of pixels -- at most
                NP = (1 + yhi - ylo) * (1 + xhi - xlo)

                A = np.zeros((NP, NT))
                A2 = np.zeros((NP, NT2))
                b = np.zeros(NP)
                w = np.zeros(NP)
                ipix = 0
                for y in range(ylo, yhi+1):
                    for x in range(xlo, xhi+1):
                        R = np.hypot(x - cx, y - cy)
                        if R > R1:
                            continue
                        rw = 1.
                        # ramp down weights from R0 to R1.
                        if R > R0:
                            rw = (R - R0) / (R1 - R0)
                        p = psfimg.get(x-px0,y-py0)
                        A[ipix,0] = p
                        A[ipix,2] = x-cx
                        A[ipix,3] = y-cy
                        b[ipix] = img.get(x, y)
                        ## FIXME -- include image variance!
                        w[ipix] = np.sqrt(rw)

                        A2[ipix,4] = (x-cx)**2
                        A2[ipix,5] = (x-cx)*(y-cy)
                        A2[ipix,6] = (y-cy)**2

                        ipix += 1
                A[:,1] = 1.

                A2[:,:4] = A[:,:4]

                # actual number of pixels
                NP = ipix
                A = A[:NP,:]
                A2 = A2[:NP,:]
                b = b[:NP]
                w = w[:NP]
                print 'Npix', NP
                A  *= w[:,np.newaxis]
                A2 *= w[:,np.newaxis]
                b  *= w
                
                X,r,rank,s = np.linalg.lstsq(A, b)
                print 'X', X

                X2,r,rank,s = np.linalg.lstsq(A2, b)
                print 'X2', X2

                SW,SH = 1+xhi-xlo, 1+yhi-ylo
                stamp = afwImage.ImageF(SW,SH)
                model = afwImage.ImageF(SW,SH)
                model2 = afwImage.ImageF(SW,SH)
                for y in range(ylo, yhi+1):
                    for x in range(xlo, xhi+1):
                        R = np.hypot(x - cx, y - cy)
                        if R > R1:
                            continue
                        stamp.set(x-xlo,y-ylo, img.get(x,y))
                        m = (psfimg.get(x-px0,y-py0) * X[0] +
                             1. * X[1] +
                             (x - cx) * X[2] +
                             (y - cy) * X[3])
                        model.set(x-xlo,y-ylo, m)
                        m = (psfimg.get(x-px0,y-py0) * X2[0] +
                             1. * X2[1] +
                             (x - cx) * X2[2] +
                             (y - cy) * X2[3] +
                             (x - cx)**2 * X2[4] +
                             (x - cx)*(y - cy) * X2[5] +
                             (y - cy)**2 * X2[6])
                        model2.set(x-xlo,y-ylo, m)
                bgsubs.append(stamp)
                models.append(model)
                models2.append(model2)


            if False:
                bgctrl = afwMath.BackgroundControl(afwMath.Interpolate.LINEAR)
                gridsz = 10.
                bgctrl.setNxSample(int(math.ceil(W / gridsz)))
                bgctrl.setNySample(int(math.ceil(H / gridsz)))
                back = afwMath.makeBackground(timg, bgctrl)
                bgsub = afwImage.ImageF(W,H)
                bgsub += timg
                bgsub -= back.getImageF()
                bgsubs.append(bgsub)
            if False:
                from scipy.ndimage.filters import median_filter
                import numpy as np
                npimg = np.zeros((H,W))
                for y in range(H):
                    for x in range(W):
                        npimg[y,x] = timg.get(x,y)
                # median filter patch size
                mfsize = 10
                mf = median_filter(npimg, mfsize) #mode='constant', cval=0.)
                bgsub = afwImage.ImageF(W,H)
                for y in range(H):
                    for x in range(W):
                        bgsub.set(x,y, timg.get(x,y) - mf[y,x])
                bgsubs.append(bgsub)


        if False:
            for pk,bgsub,timg in zip(pks, bgsubs, templs):
                # Ask for the PSF image at the integer pixel Ix() because we made
                # the template on an integer pixel grid
                #psfimg = psf.computeImage(afwGeom.Point2D(pk.getFx(), pk.getFy()))
                psfimg = psf.computeImage(afwGeom.Point2D(pk.getIx(), pk.getIy()))
                bbox = psfimg.getBBox(afwImage.PARENT)
                print 'Peak pos', pk.getFx(), pk.getFy()
                print 'PSF bbox X:', bbox.getMinX(), bbox.getMaxX()
                print 'PSF bbox Y:', bbox.getMinY(), bbox.getMaxY()
                bbox.clip(fp.getBBox())
                print 'clipped bbox X:', bbox.getMinX(), bbox.getMaxX()
                print 'clipped bbox Y:', bbox.getMinY(), bbox.getMaxY()
                px0,py0 = psfimg.getX0(), psfimg.getY0()

                numer = 0.
                denom = 0.
                for y in range(bbox.getMinY(), bbox.getMaxY()+1):
                    for x in range(bbox.getMinX(), bbox.getMaxX()+1):
                        p = psfimg.get(x-px0,y-py0)
                        numer += p * bgsub.get(x-x0, y-y0)
                        denom += p * p
                amp = numer / denom
                print 'PSF amplitude:', amp

                model = afwImage.ImageF(W,H)
                for y in range(H):
                    for x in range(W):
                        m = 0.
                        px,py = x+x0,y+y0
                        if bbox.contains(afwGeom.Point2I(px,py)):
                            m += amp * psfimg.get(px-px0, py-py0)
                        model.set(x,y, m)
                models.append(model)

        # Now apportion flux according to the templates ?
        portions = [afwImage.ImageF(W,H) for t in templs]
        for y in range(H):
            for x in range(W):
                tvals = [t.get(x,y) for t in templs]
                #S = sum([max(0, t) for t in tvals])
                S = sum([abs(t) for t in tvals])
                if S == 0:
                    continue
                for t,p in zip(tvals,portions):
                    #p.set(x,y, img.get(x0+x, y0+y) * max(0,tvals[i])/S)
                    p.set(x,y, img.get(x0+x, y0+y) * abs(t)/S)

        allp.append(portions)
        allt.append(templs)
        allbgsub.append(bgsubs)
        allmod.append(models)
        allmod2.append(models2)
    return allt, allp, allbgsub, allmod, allmod2
