#!/bin/bash
cd "$(dirname "$0")"
Rscript -e 'bookdown::render_book("ThesisDraft_v2.Rmd")'
