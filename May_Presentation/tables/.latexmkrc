# Post-build hook: emit PNG (raster) into ./rendered/ after each successful PDF
# compile. Triggered by texlab/VS Code save-build and by manual
# `latexmk -cd <file>.tex` runs.
#
# SVG generation via dvisvgm is intentionally dropped: dvisvgm requires
# Ghostscript < 10.01.0 or mutool to parse PDFs, and the system Ghostscript is
# newer. If SVG is needed, install mupdf-tools (`brew install mupdf-tools`) and
# add `dvisvgm --pdf --no-fonts --output="rendered/%R.svg" "%R.pdf"` here.
#
# Substitutions used: %R = root jobname (no extension).

$pdf_mode = 1;

$success_cmd = 'mkdir -p rendered && '
             . 'magick -density 400 "%R.pdf" -background white -alpha remove -trim "rendered/%R.png"';
