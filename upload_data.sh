#!/usr/bin/env bash
#
# Upload sample data files as release assets and print the URL and SHA-256
# for pooch.retrieve calls in irispy.
#
# Usage: TAG=v1 ./upload_data.sh file1.fits.gz file2.tar.gz ...

set -euo pipefail

REPO=${REPO:-LM-SAL/irispy-data}
TAG=${TAG:-v1}

if [ $# -eq 0 ]; then
    echo "usage: TAG=v1 $0 <file> [<file> ...]" >&2
    exit 1
fi

gh release view "$TAG" --repo "$REPO" >/dev/null 2>&1 ||
    gh release create "$TAG" --repo "$REPO" --notes "Sample data $TAG"

gh release upload "$TAG" "$@" --repo "$REPO" --clobber

echo
echo "# pooch.retrieve(url, known_hash=...) arguments:"
for f in "$@"; do
    n=$(basename "$f")
    echo "\"$n\": ("
    echo "    \"https://github.com/$REPO/releases/download/$TAG/$n\","
    echo "    \"sha256:$(sha256sum "$f" | cut -d' ' -f1)\","
    echo "),"
done
