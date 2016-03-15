import os.path

from lsst.utils import getPackageDir

config.measurement.load(os.path.join(getPackageDir("obs_subaru"), "config", "apertures.py"))
config.measurement.load(os.path.join(getPackageDir("obs_subaru"), "config", "kron.py"))
# Turn off cmodel until latest fixes (large blends, footprint merging, etc.) are in
# config.measurement.load(os.path.join(getPackageDir("obs_subaru"), "config", "cmodel.py"))

config.measurement.slots.instFlux = None

config.measurement.plugins['base_PixelFlags'].masksFpAnywhere.append('CLIPPED')
config.measurement.plugins['base_PixelFlags'].masksFpCenter.append('BRIGHT_OBJECT')
config.measurement.plugins['base_PixelFlags'].masksFpCanywhere.append('BRIGHT_OBJECT')
