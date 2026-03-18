# Template Notes

## How the template works

The template uses `bookdown::pdf_document2` which layers on top of standard R Markdown PDF output. This gives you numbered sections, cross-referencing for figures/tables/equations, and BibTeX citation support.

### YAML header

```yaml
output:
  bookdown::pdf_document2:
    toc: no
    number_sections: true
bibliography: thesis.bib
```

- `toc: no` suppresses the automatic TOC (we place it manually with `\tableofcontents` to control pagination).
- `number_sections: true` auto-numbers all `#`, `##`, `###` headings.
- `bibliography:` points to a `.bib` file in the same directory.

### Citations

Add entries to `thesis.bib` using standard BibTeX format. Cite in text with:
- `@MacDermott2025` → author-year inline: MacDermott et al. (2025)
- `[@MacDermott2025]` → parenthetical: (MacDermott et al., 2025)
- `[@MacDermott2025, p. 5]` → with page number

Citations at the end of the document are placed wherever `<div id="refs"></div>` appears (inside the `# References` section).

### Cross-referencing

| What              | Label syntax              | Reference syntax              |
|-------------------|---------------------------|-------------------------------|
| Section/Chapter   | `\label{chap:intro}`      | `\ref{chap:intro}`            |
| Equation (LaTeX)  | `\label{eqn:m1}`          | `(\ref{eqn:m1})`              |
| Figure (R chunk)  | chunk name `fig-name`     | `\@ref(fig:fig-name)`         |
| Table (kable)     | chunk name `tab-name`     | `\@ref(tab:tab-name)`         |

Equations must be in a `\begin{equation}...\end{equation}` block (not `$$...$$`) to be numbered. Use `$$...$$` for display equations you don't need to reference.

### R chunks

- `echo = FALSE` hides code from output (use for all production figures/tables).
- `include = FALSE` runs code silently with no output at all (use for setup).
- `fig.cap = "..."` is required for bookdown to number and cross-reference figures.

### Building to PDF

Open `ThesisDraft.Rmd` in RStudio and click **Knit**, or from the R console:

```r
bookdown::render_book("ThesisDraft.Rmd")
```

Requires: `bookdown`, `knitr`, `ggplot2`, `GGally` (for example plots), and a LaTeX distribution (TinyTeX recommended: `tinytex::install_tinytex()`).

### Title page and declaration

These use raw LaTeX (`\begin{titlepage}`, `\clearpage`, etc.) directly in the `.Rmd` file. They appear before the TOC and before any numbered sections.

### Bib file structure

The `thesis.bib` file uses standard BibTeX entry types: `@misc`, `@article`, `@book`, `@inproceedings`, `@phdthesis`, `@manual`. Only entries that are actually cited in the `.Rmd` will appear in the References section. To force an entry to appear without citing it, add to the YAML:

```yaml
nocite: |
  @MacDermott2025
```
