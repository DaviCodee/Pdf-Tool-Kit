# Pdf-Tool-Kit

Concentrador de operações de PDF: um **núcleo Python** com um registro único de
operações, exposto por adaptadores finos de **CLI** e **API**. Serve de base para
ferramentas gráficas, de linha de comando e serviços.

A ideia central: cada operação é declarada **uma vez** (lógica + parâmetros tipados em
Pydantic) e aparece automaticamente na CLI e na API.

## Arquitetura

```
core/        contratos e utilitários (operação, registro, parâmetros, intervalos,
             validação, workspace, erros) — sem dependência de libs de PDF
engines/     wrappers finos sobre pypdf (estrutural), pikepdf (fallback) e
             reportlab (geração de overlays)
operations/  uma operação por módulo; é onde mora a lógica de negócio
cli/         app Typer gerado a partir do registro
api/         app FastAPI gerado a partir do registro
```

Motor estrutural: **pypdf** (BSD, Python puro). O núcleo é leve e permissivo; motores
mais pesados (render/OCR via PyMuPDF, Ghostscript) ficam reservados para *extras*
opcionais futuros.

## Operações disponíveis

**Tier 1 — estrutural (sem dependências extras):**
`merge`, `split`, `remove-pages`, `extract-pages`, `reorder-pages`, `rotate`, `crop`,
`protect`, `unlock`, `metadata-read`, `metadata-edit`, `page-numbers`, `watermark`,
`optimize-web`.

**Tier 2 — render/conversão (requer extras opcionais):**

| Operação | Extra / binário |
| --- | --- |
| `pdf-to-image` (PDF → PNG/JPG) | `render` (PyMuPDF) |
| `thumbnail` (miniaturas) | `render` (PyMuPDF) |
| `images-to-pdf` (imagens → PDF) | `images` (Pillow) |
| `compress` (Ghostscript) | binário `gs` |
| `ocr` (camada de texto) | `ocr` (ocrmypdf) + binário `tesseract` |
| `extract-tables` (→ CSV) | `tables` (pdfplumber) |

**Tier 3 — assinatura, redação, comparação, formulários e Office:**

| Operação | Extra / binário |
| --- | --- |
| `sign` (assinatura digital) | `sign` (pyHanko); `.pfx` do usuário ou cert efêmero |
| `redact` (remoção real de conteúdo) | `render` (PyMuPDF) |
| `compare` (diff de texto entre 2 PDFs) | **base** |
| `form-read` / `form-fill` | **base** (pypdf) |
| `office-to-pdf` (Office → PDF) | binário `soffice` (LibreOffice) |
| `pdf-to-word` (PDF → .docx) | `office` (pdf2docx) |

Operações que dependem de extras sempre aparecem em `ptk list` e na API; se a dependência
não estiver instalada, a execução falha com uma mensagem clara
(`MissingDependencyError` → HTTP 501).

Intervalos de páginas usam notação 1-based: `1-3,5,8-` (do 8 até o fim), `-2`
(do início até o 2), `4-2` (invertido).

## Instalação

```bash
uv venv && uv pip install -e ".[cli,api,dev]"
```

Extras: `cli` (Typer), `api` (FastAPI/uvicorn), `render` (PyMuPDF), `images` (Pillow),
`ocr` (ocrmypdf), `tables` (pdfplumber), `sign` (pyHanko), `office` (pdf2docx),
`dev` (pytest/ruff/mypy). Recursos que dependem de binários do sistema: `compress` (`gs`),
`ocr` (`tesseract`), `office-to-pdf` (`soffice`/LibreOffice).

## Uso — CLI

```bash
ptk list                                  # lista as operações
ptk schema split                          # schema JSON dos parâmetros
ptk run merge a.pdf b.pdf -o saida/       # junta PDFs
ptk run split doc.pdf -p every=2 -o out/  # divide a cada 2 páginas
ptk run rotate doc.pdf -p degrees=90 -p pages=1-2 -o out/
ptk run watermark doc.pdf -p text=RASCUNHO -o out/
ptk run metadata-read doc.pdf             # imprime JSON
```

Parâmetros: `-p chave=valor` (repita a chave para campos de lista, ex.:
`-p ranges=1-2 -p ranges=3-5`) ou `--json '{"every": 2}'`.

## Uso — API

```bash
uvicorn pdftoolkit.api.app:app --reload
```

- `GET  /operations` — lista as operações
- `GET  /operations/{nome}/schema` — schema dos parâmetros
- `POST /operations/{nome}` — multipart com `files` e `params` (JSON). Retorna o PDF,
  um ZIP (quando há vários artefatos) ou JSON (operações de leitura). Docs em `/docs`.

## Desenvolvimento

```bash
pytest          # testes (operações geram PDFs em runtime; nada binário é commitado)
ruff check src tests
mypy
```

## Política de originalidade

Bibliotecas de terceiros são usadas apenas como dependências, via API pública. Nenhum
código-fonte externo é copiado; referências serviram só para capacidades e licenças.
