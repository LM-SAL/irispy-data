# irispy-data

Sample and test data for [irispy](https://github.com/LM-SAL/irispy), stored as
release assets. Keep data files out of git.

## Adding or updating data

With an authenticated [GitHub CLI](https://cli.github.com/), run:

```bash
./upload_data.sh file1.fits.gz file2.tar.gz
```

The script creates the `v1` release if needed, replaces assets with matching
names, and prints their download URLs and SHA-256 hashes.

Update the URLs and SHA-256 hashes in irispy’s `pooch.retrieve` calls when
adding or changing a file.
