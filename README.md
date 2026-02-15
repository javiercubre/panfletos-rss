# Panfletos RSS Feed

RSS feed atualizado automaticamente para o programa **Panfletos** (Pedro Tadeu, Antena 1 - RTP).

O feed oficial da RTP parou de ser atualizado em 2021. Este repositório gera um feed RSS a partir do [RTP Play](https://www.rtp.pt/play/p8339/panfletos) e publica-o via GitHub Pages.

## Como usar

Depois de configurado (ver abaixo), o teu feed RSS estará disponível em:

```
https://<teu-username>.github.io/panfletos-rss/panfletos.xml
```

Basta adicionar esse URL ao teu leitor RSS favorito (Feedly, Inoreader, AntennaPod, Overcast, etc.).

## Setup (passo a passo)

### 1. Cria o repositório no GitHub

Vai a [github.com/new](https://github.com/new) e cria um repositório com o nome `panfletos-rss` (público).

### 2. Faz push dos ficheiros

```bash
cd panfletos-rss
git init
git add .
git commit -m "Initial commit - Panfletos RSS feed generator"
git branch -M main
git remote add origin https://github.com/<teu-username>/panfletos-rss.git
git push -u origin main
```

### 3. Ativa GitHub Pages

1. Vai a **Settings** → **Pages** no teu repositório
2. Em **Source**, seleciona **GitHub Actions**
3. Guarda

### 4. Corre o workflow

1. Vai a **Actions** no teu repositório
2. Clica em **"Update Panfletos RSS Feed"** na barra lateral
3. Clica em **"Run workflow"** → **"Run workflow"**
4. Aguarda ~1 minuto

### 5. Subscreve o feed

O teu feed estará disponível em:

```
https://<teu-username>.github.io/panfletos-rss/panfletos.xml
```

O feed é atualizado automaticamente a cada 6 horas via GitHub Actions.

## Estrutura

```
├── .github/workflows/update-feed.yml   # GitHub Actions (cron a cada 6h)
├── panfletos_rss_generator.py           # Script que faz scraping e gera o XML
├── index.html                           # Landing page do GitHub Pages
├── requirements.txt                     # Dependências Python
└── site/                                # Pasta gerada pelo workflow
```

## Notas

- O script faz scraping da página do RTP Play para extrair os episódios mais recentes
- Se o scraping falhar, usa dados hardcoded como fallback
- O feed inclui metadados iTunes/podcast para compatibilidade com apps de podcast
- Este é um projeto não oficial, sem qualquer associação à RTP
