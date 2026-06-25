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
             LibreOffice, qrcode), com importação preguiçosa das dependências opcionais
operations/  lógica de cada operação, declarada com @register; fica disponível
             automaticamente na CLI e na API
cli/         app Click gerado a partir do registro (um subcomando por operação)
api/         app FastAPI gerado a partir do registro
```

Motor estrutural: **pypdf** (BSD, Python puro), com **pikepdf** como motor secundário.
O núcleo é leve e permissivo; os motores mais pesados (PyMuPDF, Ghostscript, OCR,
Office, assinatura) entram apenas como *extras opcionais* — instale só o que for usar.
Operações cujo extra não está presente continuam listadas, mas falham na execução com uma
mensagem clara (`MissingDependencyError` → HTTP 501).

## Operações disponíveis

**58 operações** organizadas por categoria. Veja todas com `ptk list`.

### Organizar / estrutura de páginas

| Operação | Descrição | Extra |
|---|---|---|
| `merge` | Junta múltiplos PDFs em ordem | — |
| `merge-folders` | Junta múltiplos PDFs em ordem alfabética | — |
| `merge-ocr` | Aplica OCR em cada PDF e une em um só | `ocr` |
| `split` | Divide por N páginas ou intervalos | — |
| `split-by-size` | Divide em partes com tamanho máximo em MB | — |
| `remove-pages` | Remove páginas indicadas | — |
| `extract-pages` | Extrai páginas para novo PDF | — |
| `reorder-pages` | Reordena páginas | — |
| `insert-pages` | Insere páginas de outro PDF em posição indicada | — |
| `add-blank` | Insere páginas em branco | — |
| `remove-blank` | Detecta e remove páginas em branco | `render` |
| `rotate` | Gira páginas por múltiplo de 90° | — |
| `batch-rotate` | Gira múltiplos PDFs de uma vez | — |
| `crop` | Recorta as páginas | — |

### Layout

| Operação | Descrição | Extra |
|---|---|---|
| `nup` | N páginas por folha (2-up, 4-up…) com vetores preservados | — |
| `page-size` | Altera o tamanho das páginas (A4, letter, etc.) | — |

### Otimizar

| Operação | Descrição | Extra |
|---|---|---|
| `compress` | Recomprime imagens (Ghostscript) | `gs` |
| `batch-compress` | Comprime múltiplos PDFs de uma vez | `gs` |
| `optimize-web` | Lineariza para carregamento progressivo na web | — |

### Converter

| Operação | Descrição | Extra |
|---|---|---|
| `pdf-to-image` | Rasteriza páginas para PNG/JPG | `render` |
| `thumbnail` | Gera miniaturas PNG | `render` |
| `images-to-pdf` | Combina imagens em um PDF | `images` |
| `to-pdfa` | Converte para PDF/A (arquivo de longa duração) | `gs` |
| `repair` | Tenta reparar PDF corrompido | `gs` |
| `office-to-pdf` | Converte documentos Office para PDF | `soffice` |
| `pdf-to-word` | Converte PDF para .docx | `office` |

### Editar conteúdo

| Operação | Descrição | Extra |
|---|---|---|
| `watermark` | Insere marca d'água de texto diagonal | — |
| `add-text` | Insere texto em posição absoluta | — |
| `add-image` | Insere imagem (PNG/JPG) em posição absoluta | — |
| `stamp` | Aplica um PDF como carimbo por cima | — |
| `overlay` | Compõe um PDF sobre ou sob outro | — |
| `qr-embed` | Gera e embute um QR code | `qr` |
| `page-numbers` | Numera páginas em posição configurável | — |
| `bates` | Numeração Bates (prefixo + nº + sufixo) | — |

### Formulários

| Operação | Descrição | Extra |
|---|---|---|
| `form-read` | Lista campos e valores de formulário | — |
| `form-fill` | Preenche campos de formulário | — |
| `fill-flatten` | Preenche e achata (torna não editável) | — |
| `flatten` | Achata todas as anotações interativas | — |

### Segurança

| Operação | Descrição | Extra |
|---|---|---|
| `protect` | Adiciona senha e permissões (AES-256) | — |
| `encrypt-advanced` | Criptografia com controle individual de cada permissão | — |
| `unlock` | Remove proteção por senha | — |
| `redact` | Remove permanentemente texto por termo ou regex | `render` |
| `redact-regex` | Remove permanentemente texto por expressão regular | `render` |

### OCR

| Operação | Descrição | Extra |
|---|---|---|
| `ocr` | Adiciona camada de texto pesquisável | `ocr` + `tesseract` |

### Tabelas

| Operação | Descrição | Extra |
|---|---|---|
| `extract-tables` | Extrai tabelas para CSV | `tables` |

### Assinatura digital

| Operação | Descrição | Extra |
|---|---|---|
| `sign` | Assina digitalmente (.pfx ou cert efêmero) | `sign` |

### Metadados e informações

| Operação | Descrição | Extra |
|---|---|---|
| `metadata-read` | Lê metadados do documento | — |
| `metadata-edit` | Atualiza campos de metadados | — |
| `remove-metadata` | Remove todos os metadados (/Info e XMP) | — |
| `compare` | Compara o texto de dois PDFs | — |
| `validate` | Verifica integridade estrutural | — |
| `font-list` | Lista fontes referenciadas | — |
| `headers` | Informa versão, tamanho de páginas, formulários, etc. | — |

### Marcadores

| Operação | Descrição | Extra |
|---|---|---|
| `bookmark` | Adiciona marcadores (outline) | — |
| `list-bookmarks` | Lista marcadores do documento | — |

### Anexos

| Operação | Descrição | Extra |
|---|---|---|
| `add-attachment` | Embute um arquivo como anexo | — |
| `extract-attachment` | Extrai todos os anexos embutidos | — |
| `list-attachments` | Lista arquivos embutidos | — |

---

Intervalos de páginas (parâmetro `--pages`/`pages`) usam notação 1-based:
`1-3,5,8-` (do 8 até o fim), `-2` (do início até o 2), `4-2` (invertido).

## Instalação

```bash
# Núcleo + CLI + API (sem extras opcionais)
uv venv && uv pip install -e ".[cli,api]"

# Tudo (inclui todos os extras Python; binários do sistema à parte)
uv pip install -e ".[cli,api,render,images,ocr,tables,sign,office,qr,dev]"
```

| Extra | Biblioteca | Para que serve |
|---|---|---|
| `cli` | Click | Interface de linha de comando |
| `api` | FastAPI + uvicorn | Servidor HTTP |
| `render` | PyMuPDF (AGPL) | Rasterização, detecção de páginas em branco, redação |
| `images` | Pillow | Conversão de imagens para PDF |
| `ocr` | ocrmypdf | Camada de texto por OCR |
| `tables` | pdfplumber | Extração de tabelas |
| `sign` | pyHanko | Assinatura digital |
| `office` | pdf2docx | PDF → Word |
| `qr` | qrcode[pil] | Geração de QR codes |
| `dev` | pytest / ruff / mypy | Desenvolvimento |

**Binários do sistema** (independentes dos extras Python):

| Binário | Necessário para |
|---|---|
| `gs` (Ghostscript) | `compress`, `batch-compress`, `to-pdfa`, `repair` |
| `tesseract` | `ocr` |
| `soffice` (LibreOffice) | `office-to-pdf` |

## Uso — CLI

Cada operação é um subcomando próprio, com flags tipadas derivadas do seu modelo de
parâmetros:

```bash
ptk list                                        # lista as 58 operações
ptk schema split                                # schema JSON dos parâmetros
ptk <operacao> --help                           # ajuda e flags de uma operação

ptk merge a.pdf b.pdf -o saida/
ptk split doc.pdf --every 2 -o out/
ptk split doc.pdf --ranges 1-2 --ranges 3-5 -o out/
ptk rotate doc.pdf --degrees 90 --pages 1-2 -o out/
ptk compress doc.pdf --quality screen -o out/
ptk watermark doc.pdf --text RASCUNHO -o out/
ptk nup doc.pdf --n 4 --paper a4 -o out/
ptk qr-embed doc.pdf --content "https://exemplo.com" --x 20 --y 20 -o out/
ptk bates doc.pdf --prefix "DOC-" --digits 5 -o out/
ptk form-fill form.pdf --values nome=Davi --values cpf=000 -o out/
ptk metadata-read doc.pdf                       # operações de leitura imprimem JSON
ptk validate doc.pdf
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
pytest          # 86 testes; PDFs gerados em runtime, nada binário commitado
ruff check src tests
mypy
```

## Política de originalidade

Bibliotecas de terceiros são usadas apenas como dependências, via API pública. Nenhum
código-fonte externo é copiado; referências serviram só para capacidades e licenças.
