"""
Build ``chianti_dbase_o4.h5``: a fiasco HDF5 database holding every non-ion CHIANTI file but only the O IV ion files.

The irispy gallery (``analysis/06_oiv_density_diagnostics``) only needs O IV, so this replaces the full ~1 GB database.

Usage: python build_chianti_subset.py <CHIANTI ASCII root> <output .h5>
"""

import sys
from pathlib import Path

from fiasco.util.setup_db import build_hdf5_dbase
from fiasco.util.util import get_chianti_catalog

ascii_root, out = Path(sys.argv[1]), Path(sys.argv[2])
catalog = get_chianti_catalog(ascii_root)
files = [name for key, names in catalog.items() if key != "ion_files" for name in names]
files += [name for name in catalog["ion_files"] if name.split(".")[0] == "o_4"]
build_hdf5_dbase(ascii_root, out, files=files, overwrite=True, show_progress=False)
