#!/usr/bin/env bash
set -euo pipefail

# Backend code is unchanged. Publish compiled assets before the new index/SW.
release_dir=${1:?Usage: deploy_task_text_frontend.sh RELEASE_DIRECTORY}
source_dir=$(realpath "$release_dir/pwa/dist")
target_dir=$(realpath /var/www/hyperum)
[[ "$target_dir" == /var/www/hyperum ]] || { echo 'Unexpected nginx root'; exit 1; }
[[ -f "$source_dir/index.html" && -f "$source_dir/sw.js" && -d "$source_dir/assets" ]]
mkdir -p "$target_dir/assets"
cp -a "$source_dir/assets/." "$target_dir/assets/"
find "$source_dir" -mindepth 1 -maxdepth 1 -type d ! -name assets \
    -exec cp -a {} "$target_dir/" \;
find "$source_dir" -maxdepth 1 -type f ! -name index.html ! -name sw.js \
    -exec cp -a {} "$target_dir/" \;
cp "$source_dir/index.html" "$target_dir/.index-normalization.html"
chmod 644 "$target_dir/.index-normalization.html"
mv "$target_dir/.index-normalization.html" "$target_dir/index.html"
cp "$source_dir/sw.js" "$target_dir/.sw-normalization.js"
chmod 644 "$target_dir/.sw-normalization.js"
mv "$target_dir/.sw-normalization.js" "$target_dir/sw.js"
nginx -t
systemctl reload nginx
echo 'Frontend deployed; previous assets retained for existing clients.'
