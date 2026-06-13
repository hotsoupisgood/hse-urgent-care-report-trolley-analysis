#!/bin/bash
cd "$(dirname "$0")"
rm -f _main.aux _main.tex _main.log _main.toc _main.lof _main.lot _main.out _main.bbl _main.blg _main.knit.md
Rscript -e 'bookdown::render_book("ThesisDraft_v2.Rmd")'
