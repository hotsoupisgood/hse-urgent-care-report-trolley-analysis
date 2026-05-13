#!/usr/bin/env bash
# Render every *.tex in this folder to PNG (raster) and SVG (vector).
# Output: ./rendered/<name>.png and ./rendered/<name>.svg
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
OUT="$DIR/rendered"

command -v pdflatex >/dev/null || { echo "pdflatex not found (install MacTeX/BasicTeX)"; exit 1; }
command -v magick   >/dev/null || { echo "magick not found (brew install imagemagick)"; exit 1; }
command -v dvisvgm  >/dev/null || { echo "dvisvgm not found (ships with TeX Live; otherwise: brew install dvisvgm)"; exit 1; }

mkdir -p "$OUT"

shopt -s nullglob
texs=( "$DIR"/*.tex )
if [ ${#texs[@]} -eq 0 ]; then
    echo "no .tex files in $DIR"
    exit 0
fi

for tex in "${texs[@]}"; do
    name="$(basename "$tex" .tex)"
    echo "[render] $name"
    pdflatex -interaction=nonstopmode -halt-on-error \
             -output-directory="$OUT" "$tex" >/dev/null
    magick -density 400 "$OUT/$name.pdf" \
           -background white -alpha remove -trim \
           "$OUT/$name.png"
    dvisvgm --pdf --no-fonts --output="$OUT/$name.svg" "$OUT/$name.pdf" >/dev/null 2>&1
done

# tidy aux files; keep PDFs in case you want them
rm -f "$OUT"/*.aux "$OUT"/*.log "$OUT"/*.out "$OUT"/*.fls "$OUT"/*.fdb_latexmk
n_png=$(ls "$OUT"/*.png 2>/dev/null | wc -l | tr -d ' ')
n_svg=$(ls "$OUT"/*.svg 2>/dev/null | wc -l | tr -d ' ')
echo "[done] $n_png PNG(s), $n_svg SVG(s) in $OUT"
