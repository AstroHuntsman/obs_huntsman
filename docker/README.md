## Tools for running the Huntsman LSST stack with Docker

This readme describes how to setup your computer and environment to run the Huntsman LSST DRP.

### Requirements

Install the Docker engine, available at a [link here](https://docs.docker.com/get-docker/).

Then run the following to install `docker-compose` on your computer: 

```
pip install docker-compose
```

Ensure that the required environment variables are set:

- `$OBS_HUNTSMAN` should point to the `obs_huntsman` directory.
- `$OBS_HUNTSMAN_TESTDATA` should point to a directory containing "science" and "calib" subdirectories, each containing appropriate FITS images. Note that Docker can't mount symlinks, so they should be actual FITS files.

#### Obtaining Huntsman test data

There are some files available to test out this DRP fairly quickly. The test data also gives an example of the directory structure.

Clone the Huntsman test data repo available [at this link](https://github.com/AstroHuntsman/test_metah_data). The relevant directory is `test_obs_huntsman`.

Note, astrometric reference catalog was created using a script in the current `obs_huntsman` repo: `scripts/querySkyMapper.py`


### Starting up Docker Huntsman DRP container

Make sure your Docker engine is running.

Then start up the Huntsman DRP docker container:

```
cd $OBS_HUNTSMAN/docker
docker-compose run lsst_stack
```
### Ingest raw science and calibration images (raw)

```
cd $LSST_HOME
ingestImages.py DATA testdata/science/*.fits* --mode=link --calib DATA/CALIB
ingestImages.py DATA testdata/calib/*.fits* --mode=link --calib DATA/CALIB
```

Note here that since we are using raw (i.e. not master) calibration files, we use `ingestImages.py` here. If they were master calibration frames, `ingestCalibs.py` should be used instead.

## Create and ingest the astrometry catalogue (refcat)

```
# Prepare the reference catalogue in LSST format
python $OBS_HUNTSMAN/scripts/ingestSkyMapperReference.py

# Move the ingested catalogue into the desired repo's ref_cats directory
cd $LSST_HOME
mkdir DATA/ref_cats
ln -s $LSST_HOME/testdata/ref_cats/skymapper_test/ref_cats/skymapper_dr3 DATA/ref_cats/
```

## Create & ingest master calibration images (biases, flats)
```
python $OBS_HUNTSMAN/scripts/constructHuntsmanBiases.py 2018-05-16
python $OBS_HUNTSMAN/scripts/constructHuntsmanBiases.py 2018-08-06
python $OBS_HUNTSMAN/scripts/constructHuntsmanFlats.py 2018-05-16
```

## Process the data to produce calibrated images (calexps)
```
processCcd.py DATA --rerun processCcdOutputs --calib DATA/CALIB --id dataType=science
```

## Make a SkyMap
```
makeDiscreteSkyMap.py DATA --id --rerun processCcdOutputs:coadd
```

## Warp calexps onto the SkyMap
```
makeCoaddTempExp.py DATA --rerun coadd --selectId filter=g2 --id filter=g2 tract=0 patch=0,0^0,1^0,2^1,0^1,1^1,2^2,0^2,1^2,2 --config doApplyUberCal=False
```

## Make the coadds
```
assembleCoadd.py DATA --rerun coadd --selectId filter=g2 --id filter=g2 tract=0 patch=0,0^0,1^0,2^1,0^1,1^1,2^2,0^2,1^2,2
```
