#!/usr/bin/env bash
# Assemble the published site: site/public/, the shared brand icons from docs/assets/ (copied, not
# duplicated in Git) and the site URL from site/SITE_URL in place of %SITE_URL%.
# Usage: site/scripts/build.sh [OUT_DIR]   (default: _site/ at the repository root, rebuilt each run)
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
out="${1:-$root/_site}"
site_url="$(tr -d '[:space:]' < "$root/site/SITE_URL")"

if [ "$out" = "$root/_site" ]; then
  rm -rf "$out"
elif [ -e "$out" ] && [ -n "$(ls -A "$out")" ]; then
  echo "error: $out exists and is not empty" >&2
  exit 1
fi

mkdir -p "$out/assets"
cp -R "$root/site/public/." "$out/"
cp "$root/docs/assets/icon.svg" "$root/docs/assets/icon.png" "$out/assets/"
for page in "$out"/*.html; do
  # Portable in-place edit (GNU and BSD sed differ on -i).
  sed "s|%SITE_URL%|$site_url|g" "$page" > "$page.tmp"
  mv "$page.tmp" "$page"
done
echo "Site assembled in $out"
