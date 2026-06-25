# Thesis

We started from the manuscript template in `Template/` and switched to the arXiv template in `arxiv/` for the final draft submission.

## Render to PDF

```bash
cd thesis && Rscript -e 'bookdown::render_book("bookdown_draft_old/thesis.Rmd")'
```

Output: `_book/_main.pdf`
