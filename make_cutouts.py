"""
Build the cut-down IRIS Level 2 tarballs used by the irispy gallery.

Each cutout keeps only the raster scans and spectral windows its examples read. The kept
FITS extensions are copied byte for byte; the primary header only loses the keywords of the
dropped windows, and the remaining per-window keywords (``TDESC1``, ``TWAVE1``, ...) are
renumbered to match the new extension order. The auxiliary and text extensions stay last.

The SDO cutout keeps every AIA channel but only the frames in the first minutes of each,
cutting the cube, the auxiliary rows and the text-table rows to match.

Usage: python make_cutouts.py <output directory>
"""

import io
import re
import sys
import tarfile
from pathlib import Path

import pooch

from astropy.io import fits

ARCHIVE = "https://www.lmsal.com/solarsoft/irisa/data/level2_compressed"
# Observation: (SHA-256 of the archive tarball, windows to keep, scan indices to keep or None for all)
CUTOUTS = {
    # analysis/01, 04, 07 (how_to/03 uses the full archive tarball)
    "20180102_153155_3610108077": (
        "8949562149cfa5fba067b5b102e8434b14cea3c3416dd79c06b7f6e211c61a39",
        ["Si IV 1403", "Mg II k 2796"],
        None,
    ),
    # analysis/02
    "20140708_114109_3824262996": (
        "21cff86fd0064936ce6807b1334ea1d3d50f3d358e5888810fba8e9bc1118567",
        ["Mg II k 2796"],
        None,
    ),
    # analysis/03
    "20130902_163935_4000255147": (
        "445c495cb6e4bdd8b563b318589691e3f4da79ee0e507d5ea587f1bd995fcb22",
        ["Mg II k 2796", "C II 1336"],
        None,
    ),
    # analysis/05, 08
    "20210429_110908_3660259102": (
        "6d07f8dfa4c4644f26dce0c63166d22900d263d555c3d142454ff27fe257688b",
        ["Si IV 1403"],
        None,
    ),
    # coalign/03, analysis/08
    "20130902_182935_4000005156": (
        "91211a52e278fb6e535242d4d6064facf9f93cf24f0a433c276ace1b2d621e7d",
        ["Si IV 1403", "Mg II k 2796", "C II 1336"],
        [0],
    ),
    # how_to/04
    "20250328_225628_3400109360": (
        "ce46e93a8962b04da344c203c4f75a8d7411d1f587e25d728a6ca8398208de1a",
        ["Mg II k 2796"],
        [0],
    ),
    # calibration/01
    "20260209_215233_3602506433": (
        "bad4a3617d0fd04679203951d7db595df196f79b41a3f6f1f71ce0e301486434",
        ["Si IV 1403"],
        [10],
    ),
    # calibration/03
    "20260308_051050_3893012099": (
        "b76277ae89e79f50e7ddc603a86b9bbf70e23b2e64fc5343dbe99af19a05f854",
        ["Mg II k 2796", "Si IV 1394"],
        None,
    ),
}

# how_to/05: observation, SHA-256 of the archive SDO tarball, minutes of each AIA channel to keep
SDO_CUTOUT = ("20250519_165924_3640107442", "b77d693fa328a96aec78b4a4aa420d5b167f8f670719fce815836627ed567f42", 5)


def cut_primary_header(header, keep):
    """
    Drop the per-window keywords of windows not in ``keep`` and renumber the rest from 1.
    """
    nwin = header["NWIN"]
    suffixes = {}
    for key in header:
        match = re.fullmatch(r"(.*?)(\d+)", key)
        if match:
            suffixes.setdefault(match[1], set()).add(int(match[2]))
    # Per-window keywords are exactly the prefixes numbered 1..NWIN (DATAP01 etc. are not).
    prefixes = [prefix for prefix, found in suffixes.items() if found == set(range(1, nwin + 1))]
    header = header.copy()
    for window in set(range(1, nwin + 1)) - set(keep):
        for prefix in prefixes:
            del header[f"{prefix}{window}"]
    # Ascending order never renames onto a keyword that still exists.
    for new, old in enumerate(keep, 1):
        if new != old:
            for prefix in prefixes:
                header.rename_keyword(f"{prefix}{old}", f"{prefix}{new}")
    header["NWIN"] = len(keep)
    return header


def cut_raster_fits(raw, windows):
    with fits.open(io.BytesIO(raw), do_not_scale_image_data=True) as hdul:
        primary = hdul[0].header
        names = [primary[f"TDESC{i}"] for i in range(1, primary["NWIN"] + 1)]
        keep = sorted(names.index(window) + 1 for window in windows)
        cut = fits.HDUList(
            [
                fits.PrimaryHDU(hdul[0].data, cut_primary_header(primary, keep)),
                *(hdul[i] for i in keep),
                hdul[-2],
                hdul[-1],
            ],
        )
        out = io.BytesIO()
        cut.writeto(out, output_verify="silentfix")
    return out.getvalue()


def archive_url(observation, kind):
    date = observation[:8]
    return f"{ARCHIVE}/{date[:4]}/{date[4:6]}/{date[6:]}/{observation}/iris_l2_{observation}_{kind}.tar.gz"


def make_cutout(observation, known_hash, windows, scans, out_dir):
    source = pooch.retrieve(archive_url(observation, "raster"), known_hash=known_hash)
    target = Path(out_dir) / f"iris_l2_{observation}_cutout_raster.tar.gz"
    with tarfile.open(source) as tar_in, tarfile.open(target, "w:gz") as tar_out:
        members = sorted((member for member in tar_in.getmembers() if member.isfile()), key=lambda m: m.name)
        for index in range(len(members)) if scans is None else scans:
            member = members[index]
            data = cut_raster_fits(tar_in.extractfile(member).read(), windows)
            member.size = len(data)
            tar_out.addfile(member, io.BytesIO(data))
    print(f"{target.name}: {target.stat().st_size / 1e6:.1f} MB")


def cut_aia_frames(raw, minutes):
    """
    Keep the frames of one AIA cube within ``minutes`` of its first frame.
    """
    with fits.open(io.BytesIO(raw), do_not_scale_image_data=True) as hdul:
        times = hdul[1].data[:, hdul[1].header["TIME"]]
        n = int((times < times[0] + minutes * 60).sum())
        out = io.BytesIO()
        fits.HDUList([fits.PrimaryHDU(hdul[0].data[:n], hdul[0].header), fits.ImageHDU(hdul[1].data[:n], hdul[1].header)]).writeto(out)
        # astropy cannot parse this text table (its TFORMs are 'A0'), so cut its fixed-width rows as bytes.
        table = hdul.fileinfo(2)
        header = hdul[2].header.copy()
        header["NAXIS2"] = n
        rows = raw[table["datLoc"] : table["datLoc"] + n * header["NAXIS1"]]
    out.write(header.tostring().encode())
    out.write(rows + b" " * (-len(rows) % 2880))
    return out.getvalue(), n


def make_sdo_cutout(observation, known_hash, minutes, out_dir):
    source = pooch.retrieve(archive_url(observation, "SDO"), known_hash=known_hash)
    target = Path(out_dir) / f"iris_l2_{observation}_cutout_SDO.tar.gz"
    with tarfile.open(source) as tar_in, tarfile.open(target, "w:gz") as tar_out:
        # Keep the archive's member order, which is the order read_files returns the channels in.
        for member in (member for member in tar_in.getmembers() if member.isfile()):
            data, n = cut_aia_frames(tar_in.extractfile(member).read(), minutes)
            member.size = len(data)
            tar_out.addfile(member, io.BytesIO(data))
            print(f"  {member.name}: {n} frames")
    print(f"{target.name}: {target.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    out_dir = Path(sys.argv[1])
    out_dir.mkdir(parents=True, exist_ok=True)
    for observation, (known_hash, windows, scans) in CUTOUTS.items():
        make_cutout(observation, known_hash, windows, scans, out_dir)
    make_sdo_cutout(*SDO_CUTOUT, out_dir)
