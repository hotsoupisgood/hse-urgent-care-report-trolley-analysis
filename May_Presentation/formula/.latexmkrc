# Post-build hook: emit PNG (raster) + SVG (vector) into ./rendered/
# after each successful PDF compile. Triggered by texlab/VS Code save-build,
# and by manual `latexmk -cd <file>.tex` runs.
#
# Substitutions used: %R = root jobname (no extension).

$pdf_mode = 1;

$success_cmd = 'mkdir -p rendered && '
             . 'magick -density 400 "%R.pdf" -background white -alpha remove -trim "rendered/%R.png" && '
             . 'dvisvgm --pdf --no-fonts --output="rendered/%R.svg" "%R.pdf"';
