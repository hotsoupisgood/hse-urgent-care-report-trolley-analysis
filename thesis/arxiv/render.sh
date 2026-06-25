#!/bin/bash
cd "$(dirname "$0")"
# Render from a subfolder; knit_root_dir = parent thesis/ so ../data paths resolve as in the original.
Rscript -e 'rmarkdown::render("ThesisDraft_arxiv.Rmd", knit_root_dir = normalizePath(".."))'
