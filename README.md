# Pdf-Tool-Kit

Concentrador de operações de PDF: um **núcleo Python** com um registro único de
operações, exposto por adaptadores finos de **CLI** e **API**. Serve de base para
ferramentas gráficas, de linha de comando e serviços.

A ideia central: cada operação é declarada **uma vez** (lógica + parâmetros tipados em
Pydantic) e aparece automaticamente na CLI e na API.

## Arquitetura

```
core/        contratos e utilitários (operação, registro, parâmetros, intervalos,
             validação, workspace, processos, erros) — sem dependência de libs de PDF
engines/     wrappers finos sobre cada biblioteca/binário (pypdf, pikepdf, reportlab,
             PyMuPDF, Pillow, Ghostscript, ocrmypdf, pdfplumber, pyHanko, pdf2docx,
             LibreOffice), com importação preguiçosa das dependências opcionais
operations/  uma operação por módulo; é onde mora a lógica de negócio
cli/         app Click gerado a partir do registro (um subcomando por operação)
api/         app FastAPI gerado a partir do registro
```

Motor estrutural: **pypdf** (BSD, Python puro), com **pikepdf** de fallback. O núcleo é
leve e permissivo; os motores mais pesados (PyMuPDF, Ghostscript, OCR, Office, assinatura)
entram apenas como *extras opcionais* — instale só o que for usar. Operações cujo extra
não está presente continuam listadas, mas falham na execução com uma mensagem clara
(`MissingDependencyError` → HTTP 501).

## Operações disponíveis

27 operações organizadas em três níveis. Veja todas com `ptk list`.

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

Intervalos de páginas (parâmetro `--pages`/`pages`) usam notação 1-based:
`1-3,5,8-` (do 8 até o fim), `-2` (do início até o 2), `4-2` (invertido).

## Instalação

```bash
uv venv && uv pip install -e ".[cli,api]"          # núcleo + CLI + API
uv pip install -e ".[cli,api,render,images,ocr,tables,sign,office,dev]"  # tudo
```

Extras: `cli` (Click), `api` (FastAPI/uvicorn), `render` (PyMuPDF), `images` (Pillow),
`ocr` (ocrmypdf), `tables` (pdfplumber), `sign` (pyHanko), `office` (pdf2docx),
`dev` (pytest/ruff/mypy). Recursos que dependem de binários do sistema: `compress` (`gs`),
`ocr` (`tesseract`), `office-to-pdf` (`soffice`/LibreOffice).

## Uso — CLI

Cada operação é um subcomando próprio (gerado a partir do registro), com flags tipadas
derivadas do seu modelo de parâmetros:

```bash
ptk list                                   # lista as operações
ptk schema split                           # schema JSON dos parâmetros
ptk <operacao> --help                      # ajuda e flags de uma operação

ptk merge a.pdf b.pdf -o saida/            # junta PDFs
ptk split doc.pdf --every 2 -o out/        # divide a cada 2 páginas
ptk split doc.pdf --ranges 1-2 --ranges 3-5 -o out/   # campos de lista: repita a flag
ptk rotate doc.pdf --degrees 90 --pages 1-2 -o out/
ptk compress doc.pdf --quality screen -o out/
ptk watermark doc.pdf --text RASCUNHO -o out/
ptk form-fill form.pdf --values nome=Davi --values cpf=000 -o out/  # dict: chave=valor
ptk metadata-read doc.pdf                  # operações de leitura imprimem JSON
```

Saída: `-o/--out` define o diretório (padrão: diretório atual). Para casos avançados,
toda operação aceita também `--json '{"every": 2}'` com os parâmetros completos.

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
