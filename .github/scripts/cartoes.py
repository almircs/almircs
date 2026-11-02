"""Gera os cartões do perfil (projetos, estatísticas e linguagens) em SVG.

Roda na ação "Atualizar cartões do perfil" com o GITHUB_TOKEN e grava os
arquivos na pasta indicada. Substitui o serviço github-readme-stats, que
falha com frequência por excesso de uso.

Uso:  python cartoes.py <pasta-de-saída> [dados.json]
      Sem dados.json, busca os dados na API do GitHub (precisa de GITHUB_TOKEN).
"""
import html
import json
import os
import sys
import urllib.request

USUARIO = "almircs"
# Projetos públicos exibidos em "Projetos em destaque", na ordem da página
DESTAQUES = ["Jogo-da-Velha", "Freeway", "Aluramidi", "Flex-e-Grid", "Barbearia", "HTML-CSS"]
# Descrições usadas nos cartões (as do GitHub de alguns repositórios estão desatualizadas)
DESCRICOES = {
    "jogo-da-velha": "Jogo da velha para dois jogadores com placar, feito com HTML, CSS e JavaScript",
    "freeway": "Jogo de atravessar a estrada feito com JavaScript e p5.js, inspirado no Atari",
    "aluramidi": "Bateria virtual tocada com o mouse, o toque ou o teclado",
    "flex-e-grid": "Página de vídeos responsiva construída com Flexbox e CSS Grid",
    "barbearia": "Site institucional de três páginas com formulário de contato",
    "html-css": "Exercícios do curso de HTML5 e CSS3 do Curso em Vídeo",
}
FONTE = "'Segoe UI', Ubuntu, 'Helvetica Neue', Sans-Serif"

# Mesmas cores dos temas "dark" e "default" usados antes, para nada mudar de cara
TEMAS = {
    "escuro": dict(bg="#151515", borda="#151515", titulo="#ffffff", texto="#9f9f9f",
                   icone="#79ff97", destaque="#fe428e", trilho="#2a2a2a"),
    "claro": dict(bg="#fffefe", borda="#e4e2e2", titulo="#2f80ed", texto="#434d58",
                  icone="#4c71f2", destaque="#2f80ed", trilho="#eeeeee"),
}

CONSULTA = """
query($login: String!) {
  user(login: $login) {
    repositories(ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC, first: 100) {
      totalCount
      nodes {
        name description stargazerCount forkCount
        primaryLanguage { name color }
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name color } }
        }
      }
    }
    contributionsCollection {
      totalCommitContributions restrictedContributionsCount
      totalPullRequestContributions totalIssueContributions
      contributionCalendar { totalContributions }
    }
    pullRequests { totalCount }
    issues { totalCount }
  }
}
"""


def buscar_dados():
    token = os.environ["GITHUB_TOKEN"]
    corpo = json.dumps({"query": CONSULTA, "variables": {"login": USUARIO}}).encode()
    req = urllib.request.Request("https://api.github.com/graphql", data=corpo, headers={
        "Authorization": f"bearer {token}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        resposta = json.load(r)
    if "errors" in resposta:
        raise SystemExit(f"Erro da API: {resposta['errors']}")
    return resposta["data"]["user"]


def num(n):
    return f"{n:,}".replace(",", ".")


def esc(s):
    return html.escape(s or "", quote=True)


def quebrar(texto, limite=52):
    """Quebra a descrição em até duas linhas."""
    palavras, linhas, atual = (texto or "").split(), [], ""
    for p in palavras:
        if len(atual) + len(p) + 1 > limite and atual:
            linhas.append(atual)
            atual = p
        else:
            atual = f"{atual} {p}".strip()
    if atual:
        linhas.append(atual)
    if len(linhas) > 2:
        linhas = linhas[:2]
        linhas[1] = linhas[1][: limite - 1].rstrip() + "…"
    return linhas


ICONE_REPO = ("M2 2.5A2.5 2.5 0 014.5 0h8.75a.75.75 0 01.75.75v12.5a.75.75 0 01-.75.75h-2.5a.75.75 0 110-1.5h1.75v-2h-8a1 1 0 00-.714 1.7.75.75 0 01-1.072 1.05A2.495 2.495 0 012 11.5v-9zm10.5-1V9h-8c-.356 0-.694.074-1 .208V2.5a1 1 0 011-1h8zM5 12.25v3.25a.25.25 0 00.4.2l1.45-1.087a.25.25 0 01.3 0L8.6 15.7a.25.25 0 00.4-.2v-3.25a.25.25 0 00-.25-.25h-3.5a.25.25 0 00-.25.25z")
ICONE_ESTRELA = ("M8 .25a.75.75 0 01.673.418l1.882 3.815 4.21.612a.75.75 0 01.416 1.279l-3.046 2.97.719 4.192a.75.75 0 01-1.088.791L8 12.347l-3.766 1.98a.75.75 0 01-1.088-.79l.72-4.194L.818 6.374a.75.75 0 01.416-1.28l4.21-.611L7.327.668A.75.75 0 018 .25z")
ICONE_FORK = ("M5 3.25a.75.75 0 11-1.5 0 .75.75 0 011.5 0zm0 2.122a2.25 2.25 0 10-1.5 0v.878A2.25 2.25 0 005.75 8.5h1.5v2.128a2.251 2.251 0 101.5 0V8.5h1.5a2.25 2.25 0 002.25-2.25v-.878a2.25 2.25 0 10-1.5 0v.878a.75.75 0 01-.75.75h-4.5A.75.75 0 015 6.25v-.878zm3.75 7.378a.75.75 0 11-1.5 0 .75.75 0 011.5 0zm3-8.75a.75.75 0 100-1.5.75.75 0 000 1.5z")


def cartao_projeto(repo, t):
    W, H = 400, 120
    linhas = quebrar(DESCRICOES.get(repo["name"].lower()) or repo.get("description"))
    ling = repo.get("primaryLanguage") or {}
    partes = [f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="{esc(repo['name'])}">
<title>{esc(repo['name'])}</title>
<rect x="0.5" y="0.5" rx="4.5" width="{W-1}" height="{H-1}" fill="{t['bg']}" stroke="{t['borda']}"/>
<svg x="25" y="19" width="16" height="16" viewBox="0 0 16 16"><path fill="{t['icone']}" fill-rule="evenodd" d="{ICONE_REPO}"/></svg>
<text x="50" y="33" font-family="{FONTE}" font-size="18" font-weight="600" fill="{t['titulo']}">{esc(repo['name'])}</text>
<text font-family="{FONTE}" font-size="13" fill="{t['texto']}">''']
    for i, linha in enumerate(linhas):
        partes.append(f'<tspan x="25" y="{62 + i*18}">{esc(linha)}</tspan>')
    partes.append('</text>')
    x = 25
    if ling.get("name"):
        partes.append(f'<circle cx="{x+6}" cy="101" r="6" fill="{ling.get("color") or "#858585"}"/>'
                      f'<text x="{x+18}" y="105.5" font-family="{FONTE}" font-size="12" fill="{t["texto"]}">{esc(ling["name"])}</text>')
        x += 18 + len(ling["name"]) * 7 + 18
    for icone, valor in ((ICONE_ESTRELA, repo.get("stargazerCount", 0)), (ICONE_FORK, repo.get("forkCount", 0))):
        if valor:
            partes.append(f'<svg x="{x}" y="93" width="16" height="16" viewBox="0 0 16 16"><path fill="{t["texto"]}" fill-rule="evenodd" d="{icone}"/></svg>'
                          f'<text x="{x+21}" y="105.5" font-family="{FONTE}" font-size="12" fill="{t["texto"]}">{num(valor)}</text>')
            x += 21 + len(num(valor)) * 7 + 16
    partes.append('</svg>')
    return "\n".join(partes)


def cartao_estatisticas(u, t):
    W, H = 495, 195
    c = u["contributionsCollection"]
    repos = u["repositories"]["nodes"]
    itens = [
        ("Contribuições no último ano", c["contributionCalendar"]["totalContributions"]),
        ("Commits no último ano", c["totalCommitContributions"] + c["restrictedContributionsCount"]),
        ("Pull requests", u["pullRequests"]["totalCount"]),
        ("Issues", u["issues"]["totalCount"]),
        ("Estrelas recebidas", sum(r["stargazerCount"] for r in repos)),
        ("Repositórios públicos", u["repositories"]["totalCount"]),
    ]
    partes = [f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="Estatísticas do GitHub de {USUARIO}">
<title>Estatísticas do GitHub</title>
<rect x="0.5" y="0.5" rx="4.5" width="{W-1}" height="{H-1}" fill="{t['bg']}" stroke="{t['borda']}"/>
<text x="25" y="35" font-family="{FONTE}" font-size="18" font-weight="600" fill="{t['titulo']}">Estatísticas no GitHub</text>''']
    for i, (rotulo, valor) in enumerate(itens):
        y = 66 + i * 23
        partes.append(f'<circle cx="31" cy="{y-4.5}" r="4" fill="{t["icone"]}"/>'
                      f'<text x="45" y="{y}" font-family="{FONTE}" font-size="14" font-weight="600" fill="{t["texto"]}">{rotulo}:</text>'
                      f'<text x="300" y="{y}" font-family="{FONTE}" font-size="14" font-weight="700" fill="{t["titulo"] if t is TEMAS["claro"] else t["titulo"]}">{num(valor)}</text>')
    partes.append('</svg>')
    return "\n".join(partes)


def cartao_linguagens(u, t):
    W = 1000
    total = {}
    cores = {}
    for r in u["repositories"]["nodes"]:
        for e in r["languages"]["edges"]:
            nome = e["node"]["name"]
            total[nome] = total.get(nome, 0) + e["size"]
            cores[nome] = e["node"]["color"] or "#858585"
    soma = sum(total.values()) or 1
    top = sorted(total.items(), key=lambda kv: kv[1], reverse=True)[:8]
    H = 95 + ((len(top) + 3) // 4) * 28
    partes = [f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="Linguagens mais usadas">
<title>Linguagens mais usadas</title>
<defs><clipPath id="barra"><rect x="25" y="55" width="{W-50}" height="10" rx="5"/></clipPath></defs>
<rect x="0.5" y="0.5" rx="4.5" width="{W-1}" height="{H-1}" fill="{t['bg']}" stroke="{t['borda']}"/>
<text x="25" y="35" font-family="{FONTE}" font-size="18" font-weight="600" fill="{t['titulo']}">Linguagens mais usadas</text>
<g clip-path="url(#barra)"><rect x="25" y="55" width="{W-50}" height="10" fill="{t['trilho']}"/>''']
    x = 25.0
    for nome, tam in top:
        w = (W - 50) * tam / soma
        partes.append(f'<rect x="{x:.2f}" y="55" width="{w + 0.5:.2f}" height="10" fill="{cores[nome]}"/>')
        x += w
    partes.append('</g>')
    for i, (nome, tam) in enumerate(top):
        col, lin = i % 4, i // 4
        cx = 25 + col * 240
        cy = 95 + lin * 28
        partes.append(f'<circle cx="{cx+5}" cy="{cy-4.5}" r="5" fill="{cores[nome]}"/>'
                      f'<text x="{cx+17}" y="{cy}" font-family="{FONTE}" font-size="13" fill="{t["texto"]}">{esc(nome)} {tam*100/soma:.1f}%</text>')
    partes.append('</svg>')
    return "\n".join(partes)


def main():
    saida = sys.argv[1]
    os.makedirs(saida, exist_ok=True)
    u = json.load(open(sys.argv[2])) if len(sys.argv) > 2 else buscar_dados()
    por_nome = {r["name"].lower(): r for r in u["repositories"]["nodes"]}
    for tema, t in TEMAS.items():
        for nome in DESTAQUES:
            repo = por_nome.get(nome.lower())
            if repo:
                open(f"{saida}/projeto-{nome.lower()}-{tema}.svg", "w").write(cartao_projeto(repo, t))
            else:
                print(f"aviso: repositório {nome} não encontrado")
        open(f"{saida}/estatisticas-{tema}.svg", "w").write(cartao_estatisticas(u, t))
        open(f"{saida}/linguagens-{tema}.svg", "w").write(cartao_linguagens(u, t))
    print("cartões gerados em", saida, ":", sorted(os.listdir(saida)))


if __name__ == "__main__":
    main()
