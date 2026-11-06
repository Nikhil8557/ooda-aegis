#!/bin/sh
# Build the GitHub Pages site into docs/: landing page at /, replay dashboard at /app/.
set -e
cd "$(dirname "$0")/.."
npm run build
rm -rf docs && mkdir -p docs/app docs/assets
cp -R dist/. docs/app/
cp site/index.html docs/index.html
[ -d site/assets ] && cp -R site/assets/. docs/assets/ || true
[ -f video/out/ooda-aegis-demo.mp4 ] && cp video/out/ooda-aegis-demo.mp4 video/out/captions.srt docs/assets/ && mv docs/assets/captions.srt docs/assets/ooda-aegis-demo.srt || true
touch docs/.nojekyll
echo "site built in docs/"
