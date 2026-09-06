#!/usr/bin/env bash
# Fetches the real StudentLife sample fixture fresh from its canonical
# source, rather than this repo redistributing a copy. Run this once before
# using 00_real_studentlife_pipeline.py or 02_real_phq9_sleep_correlation.py.
set -e
TARGET="$(dirname "$0")/../real_data"
mkdir -p "$TARGET"
echo "Cloning frycast/studentlife (canonical source of the sample fixture)..."
git clone --depth 1 https://github.com/frycast/studentlife.git /tmp/sl_repo_fetch
mkdir -p "$TARGET/sl_sample"
tar xjf /tmp/sl_repo_fetch/tests/testthat/testdata/sample/sample_dataset.tar.bz2 -C "$TARGET/sl_sample"
rm -rf /tmp/sl_repo_fetch
echo "Done. Real sample data now in $TARGET/sl_sample/"
echo ""
echo "For the FULL 48-student, 10-week dataset instead of this 3-user sample:"
echo "  wget https://studentlife.cs.dartmouth.edu/dataset/dataset.tar.bz2"
echo "  (about 5GB -- point DATA_DIR at the extracted folder, same code works)"
