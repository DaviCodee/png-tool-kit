# pngtoolkit

Concentrador de operações de imagem: um **único núcleo** Python que expõe um registro
de operações, consumido por adaptadores finos de **CLI** (`pik`) e **API** (FastAPI).
A mesma operação, definida uma vez, fica disponível na linha de comando e via HTTP.

O motor estrutural é o [Pillow](https://python-pillow.org/) (licença MIT-CMU), que
cobre PNG, JPEG, WebP, GIF, BMP, TIFF e ICO nativamente. Extras opcionais adicionam
AVIF e vetorização para SVG.

## Arquitetura

```
src/pngtoolkit/
  core/        contrato (operation), registro, params (Pydantic), io, validação, erros
  engines/     pillow_engine (primário), trace (svg), avif, heif
  operations/  transform, format, exif, compose, vector  (cada @register se auto-registra)
  cli/         main.py  — Click, um subcomando por operação (pik)
  api/         app.py   — FastAPI gerada a partir do registro
```

Cada operação é uma classe `ImageOperation` com um modelo de parâmetros Pydantic.
Esse único schema alimenta a validação, as flags da CLI, o corpo da API e o export de
JSON Schema. Os adaptadores apenas percorrem o registro — não conhecem operações
individualmente.

## Instalação

```bash
pip install -e ".[cli,api]"          # núcleo + CLI + API
pip install -e ".[cli,api,avif,dev]" # tudo, incluindo testes
```

| Extra   | Habilita                                   | Requisitos de sistema            |
|---------|--------------------------------------------|----------------------------------|
| `cli`   | comando `pik`                              | —                                |
| `api`   | servidor FastAPI/uvicorn                   | —                                |
| `avif`  | AVIF em Pillow antigo (11.1+ já tem nativo)| —                                |
| `heif`  | `heic`/`heif` (leitura e gravação)         | —                                |
| `bg`**  | `remove-bg` modo `ai` (U²-Net via ONNX)    | baixa o modelo (~168MB) no 1º uso|
| `svg`*  | `png-to-svg`                               | binários `magick` e `potrace`    |
| `dev`   | pytest, ruff, mypy, httpx                  | —                                |

\* O extra `svg` não tem dependência Python: basta ter o ImageMagick (`magick`) e o
`potrace` instalados no sistema. Operações que dependem de um extra ausente continuam
listadas, mas falham na execução com `MissingDependencyError` (HTTP 501 na API).

\*\* O extra `bg` (modo `ai` do `remove-bg`) roda o modelo **U²-Net direto no
`onnxruntime`** (+ `numpy`), sem `rembg` — então instala normalmente em Python
3.11–3.14. O arquivo `.onnx` é baixado uma vez e cacheado em
`$XDG_CACHE_HOME/pngtoolkit` (por padrão `~/.cache/pngtoolkit`). O modo `color` não
precisa do extra e funciona sempre.

## Operações

| Operação      | Categoria    | Resumo                                                            |
|---------------|--------------|-------------------------------------------------------------------|
| `resize`      | transformar  | largura, altura ou porcentagem (mantém proporção)                 |
| `crop`        | transformar  | caixa de pixels ou dimensão ancorada (centro/cantos)              |
| `rotate`      | transformar  | ângulo qualquer (90/180/270 ou custom)                            |
| `flip`        | transformar  | espelho horizontal ou vertical                                    |
| `convert`     | formato      | png, jpg, webp, avif, heic*, gif, bmp, tiff, ico, jp2, pdf, tga, ppm, qoi, sgi, icns, dds, pcx, eps, xbm |
| `batch-convert`| formato     | converte toda a árvore de uma pasta, com opção de apagar originais|
| `compress`    | formato      | recompressão (quality + optimize)                                 |
| `grayscale`   | formato      | tons de cinza                                                     |
| `exif-read`   | metadados    | lê EXIF e devolve JSON (sem produzir arquivo)                     |
| `strip-exif`  | metadados    | remove EXIF e demais metadados                                    |
| `watermark`   | composição   | marca d'água de texto ou imagem (posição + opacidade)            |
| `blur`        | composição   | desfoque gaussiano total ou por região                            |
| `favicon`     | composição   | gera 16/32/180/192/512 + `favicon.ico` multi-resolução           |
| `meme`        | composição   | texto topo/base estilo impact                                     |
| `remove-bg`   | composição   | remove fundo por cor (rápido) ou por IA (extra `bg`)              |
| `png-to-svg`  | vetor        | vetorização via magick + potrace (extra `svg`)                    |

## Uso — CLI

```bash
pik list                                   # lista as operações
pik schema resize                          # schema JSON dos parâmetros
pik resize foto.png --width 800 -o out/
pik convert foto.png --format webp -o out/
pik batch-convert ./fotos --format webp                # recursivo, in-place, mantém originais
pik batch-convert ./fotos --format webp --delete-originals
pik batch-convert ./fotos -o ./out --format avif       # espelha em ./out, originais intactos
pik compress foto.jpg --quality 60 -o out/
pik watermark foto.png --text "© 2026" --position bottom-right -o out/
pik watermark foto.png logo.png --opacity 0.4 -o out/   # marca d'água de imagem
pik favicon logo.png -o out/               # gera vários tamanhos + .ico
pik png-to-svg desenho.png --threshold 60 -o out/
```

Cada flag se documenta — rode `pik <operação> --help` para ver os parâmetros e suas
descrições (geradas a partir do modelo Pydantic da operação).

### Recorte (`crop`)

Dois modos mutuamente exclusivos:

```bash
# 1) caixa explícita: 4 inteiros LEFT TOP RIGHT BOTTOM, em pixels,
#    com origem no canto superior esquerdo.
pik crop foto.png --box 10 20 210 170 -o out/    # janela x:10..210, y:20..170

# 2) janela ancorada: dimensão + onde ancorar (center ou um dos cantos).
pik crop foto.png --width 200 --height 150 --anchor center -o out/
```

### Desfoque (`blur`)

```bash
pik blur foto.png --radius 8 -o out/                       # imagem inteira
# só uma região (mesmo formato LEFT TOP RIGHT BOTTOM do crop), p.ex. borrar um rosto:
pik blur foto.png --radius 12 --region 40 30 120 110 -o out/
```

### Remoção de fundo (`remove-bg`)

```bash
# modo color (rápido, fundo uniforme): cor amostrada dos cantos, ou explícita.
pik remove-bg produto.png --method color --tolerance 30 -o out/
pik remove-bg logo.png --method color --color 255 255 255 -o out/

# modo ai (retrato/recorte genérico; requer o extra 'bg'):
pik remove-bg retrato.jpg --method ai --model u2net -o out/    # u2net = qualidade
pik remove-bg retrato.jpg --method ai --model u2netp -o out/   # u2netp = leve/rápido
```

A saída é sempre PNG (precisa de canal alfa). Sem o extra `bg`, o modo `ai` falha com
`MissingDependencyError` (HTTP 501 na API); o modo `color` funciona sempre.

Operações de múltiplas saídas (ex.: `favicon`) gravam vários arquivos no diretório
`-o`. Operações sem artefato (ex.: `exif-read`) imprimem o resultado como JSON.

### Conversão em lote (`batch-convert`)

Aplica o `convert` recursivamente sobre uma pasta. Expande diretórios filtrando por
uma whitelist de extensões (`png`, `jpg`, `webp`, `avif`, `heic`, `tiff`, `ico`,
`jp2`, `psd`, `tga`, `pcx`, `ppm`, `qoi`, etc. — sobreponível com `--ext`); preserva a
estrutura relativa de subpastas. Por padrão grava na mesma pasta da origem; com
`-o/--out` espelha a árvore em outro diretório (originais ficam intactos). Os
originais só são apagados **depois** que todos os artefatos foram escritos com
sucesso — uma falha de I/O no meio do lote preserva tudo.

## Uso — API

```bash
uvicorn pngtoolkit.api.app:app --reload    # abra http://127.0.0.1:8000/docs
```

| Rota                            | Descrição                                          |
|---------------------------------|----------------------------------------------------|
| `GET  /operations`              | lista as operações                                 |
| `GET  /operations/{name}/schema`| schema JSON dos parâmetros                          |
| `POST /operations/{name}`       | executa (multipart: `files` + `params` JSON)       |

A resposta é o próprio arquivo (uma saída), um ZIP (múltiplas saídas) ou JSON (sem
artefato). Exemplo:

```bash
curl -F "files=@foto.png" -F 'params={"width":400}' \
  http://127.0.0.1:8000/operations/resize -o saida.png
```

## Desenvolvimento

```bash
pytest                 # testes (imagens geradas em runtime; nada binário commitado)
ruff check src tests   # lint
mypy                   # tipos (strict)
```

A licença é MIT (ver `LICENSE`). Pillow e plugins são usados apenas como dependência
via API pública.
