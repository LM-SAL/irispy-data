# irispy-data

Sample and test data files for the [`irispy`](https://github.com/LM-SAL/irispy) documentation gallery and remote-data tests.

The files are **not** stored in the git tree — they are attached as release assets and downloaded on demand with [pooch](https://www.fatiando.org/pooch/), which checks their SHA-256 and caches them locally.

Download URL pattern:

```
https://github.com/LM-SAL/irispy-data/releases/download/<tag>/<filename>
```

## Adding or updating files

Use `upload_data.sh` (requires the [`gh` CLI](https://cli.github.com/), authenticated):

```bash
./upload_data.sh path/to/file1.fits.gz path/to/file2.tar.gz
```

Always upload to the `v1` tag (the default) and let it clobber same-named assets, one release holds the current copy of everything.
The script prints the URL + SHA-256 to use as `pooch.retrieve(url, known_hash=...)` in irispy; a changed file changes its hash, so update irispy in the same PR.

Notes:

- Per-file limit is 2 GB (GitHub release asset limit).
- `chianti_dbase_o4.h5` is a fiasco HDF5 database with only the O IV ion files (plus all non-ion files), built with `build_chianti_subset.py` from CHIANTI 11.0.2.
  Rebuild it when CHIANTI or fiasco change the database format.
- `iris_l2_*_cutout_raster.tar.gz` are cut-down copies of IRIS Level 2 raster tarballs from the archive, keeping only the scans and spectral windows the gallery examples read.
  `iris_l2_*_cutout_SDO.tar.gz` keeps every AIA channel of an SDO tarball but only its first five minutes.
  `make_cutouts.py` lists the source observation, windows and scans of each, and rebuilds them: `python make_cutouts.py <output directory>`.
