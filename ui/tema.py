"""Tema visual (ttk) moderno e gráficos simples desenhados em Canvas (sem matplotlib)."""
import math
import sys
import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk

# ---------------------------------------------------------------- paleta
ACENTO = "#2563eb"
ACENTO_ESCURO = "#1d4ed8"
ACENTO_CLARO = "#e8effe"
ACENTO_SUAVE = "#93b0f5"
VERDE = "#10b981"
VERDE_CLARO = "#d7f5ea"
VERMELHO = "#dc2626"
VERMELHO_CLARO = "#fee2e2"
FUNDO = "#f5f7fb"
SUPERFICIE = "#ffffff"
SUPERFICIE_ALT = "#f8fafc"
BORDA = "#e4e8ef"
TRILHO = "#eef2f7"
BORDA_BOTAO = "#d5dbe5"
TEXTO = "#111827"
TEXTO_SUAVE = "#6b7280"

# nomes antigos, mantidos por compatibilidade
AZUL, AZUL_ESCURO = ACENTO, ACENTO_ESCURO
CINZA_FUNDO, CINZA_TEXTO, BRANCO = FUNDO, TEXTO_SUAVE, SUPERFICIE

# ---------------------------------------------------------------- fontes
_PREFERIDAS = ["Segoe UI", "Inter", "SF Pro Text", "Helvetica Neue", "Noto Sans", "Cantarell", "Ubuntu", "DejaVu Sans"]
_MONO = ["Cascadia Mono", "Consolas", "Menlo", "DejaVu Sans Mono", "Courier New"]

ESC = 1.0  # fator de escala (telas HiDPI); definido em aplicar_tema


def _definir_fontes(familia: str, mono: str) -> None:
    global FAMILIA, FAMILIA_MONO, FONTE, FONTE_NEGRITO, FONTE_TITULO, FONTE_SUB, FONTE_PEQ, FONTE_PEQ_NEG, FONTE_KPI
    FAMILIA, FAMILIA_MONO = familia, mono
    FONTE = (familia, 10)
    FONTE_NEGRITO = (familia, 10, "bold")
    FONTE_TITULO = (familia, 18, "bold")
    FONTE_SUB = (familia, 11, "bold")
    FONTE_PEQ = (familia, 9)
    FONTE_PEQ_NEG = (familia, 9, "bold")
    FONTE_KPI = (familia, 22, "bold")


_definir_fontes("Segoe UI" if sys.platform.startswith("win") else "Helvetica Neue" if sys.platform == "darwin"
                else "DejaVu Sans", "Consolas" if sys.platform.startswith("win") else "DejaVu Sans Mono")


def ativar_dpi() -> None:
    """Windows: evita a interface 'borrada' em telas com escala > 100%. Chamar antes de criar o Tk."""
    if not sys.platform.startswith("win"):
        return
    try:
        import ctypes
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:  # noqa: BLE001
            ctypes.windll.user32.SetProcessDPIAware()
    except Exception:  # noqa: BLE001
        pass


def aplicar_tema(raiz: tk.Misc) -> None:
    global ESC
    ESC = max(1.0, raiz.winfo_fpixels("1i") / 96)
    instaladas = set(tkfont.families(raiz))
    familia = next((f for f in _PREFERIDAS if f in instaladas), tkfont.nametofont("TkDefaultFont").actual("family"))
    mono = next((f for f in _MONO if f in instaladas), "TkFixedFont")
    _definir_fontes(familia, mono)
    for nome in ("TkDefaultFont", "TkTextFont", "TkMenuFont"):
        tkfont.nametofont(nome).configure(family=familia, size=10)
    tkfont.nametofont("TkFixedFont").configure(family=mono, size=10)
    raiz.option_add("*TCombobox*Listbox.font", FONTE)
    raiz.option_add("*TCombobox*Listbox.selectBackground", ACENTO)
    raiz.option_add("*TCombobox*Listbox.selectForeground", SUPERFICIE)

    s = ttk.Style(raiz)
    if "clam" in s.theme_names():
        s.theme_use("clam")
    raiz.configure(bg=FUNDO)
    s.configure(".", font=FONTE, background=FUNDO, foreground=TEXTO, bordercolor=BORDA,
                lightcolor=BORDA, darkcolor=BORDA, focuscolor=ACENTO_SUAVE)

    # ---- molduras e rótulos
    s.configure("TFrame", background=FUNDO)
    s.configure("Card.TFrame", background=SUPERFICIE, relief="solid", borderwidth=1,
                bordercolor=BORDA, lightcolor=BORDA, darkcolor=BORDA)
    s.configure("Plano.TFrame", background=SUPERFICIE)
    s.configure("Barra.TFrame", background=SUPERFICIE)
    s.configure("TLabel", background=FUNDO, foreground=TEXTO)
    s.configure("Card.TLabel", background=SUPERFICIE)
    s.configure("Barra.TLabel", background=SUPERFICIE)
    s.configure("BarraMuted.TLabel", background=SUPERFICIE, foreground=TEXTO_SUAVE)
    s.configure("Muted.TLabel", foreground=TEXTO_SUAVE, background=FUNDO)
    s.configure("CardMuted.TLabel", foreground=TEXTO_SUAVE, background=SUPERFICIE, font=FONTE_PEQ)
    s.configure("Campo.TLabel", foreground=TEXTO_SUAVE, background=SUPERFICIE, font=FONTE_PEQ_NEG)
    s.configure("CampoFundo.TLabel", foreground=TEXTO_SUAVE, background=FUNDO, font=FONTE_PEQ_NEG)
    s.configure("Titulo.TLabel", font=FONTE_TITULO, background=FUNDO)
    s.configure("Sub.TLabel", font=FONTE_SUB, background=SUPERFICIE)
    s.configure("SubFundo.TLabel", font=FONTE_SUB, background=FUNDO)
    s.configure("Valor.TLabel", font=FONTE_KPI, background=SUPERFICIE)
    s.configure("Erro.TLabel", foreground=VERMELHO, background=FUNDO)
    s.configure("ErroCard.TLabel", foreground=VERMELHO, background=SUPERFICIE)
    s.configure("TCheckbutton", background=SUPERFICIE)
    s.configure("Card.TCheckbutton", background=SUPERFICIE, foreground=TEXTO_SUAVE, font=FONTE_PEQ)
    s.configure("Card.TCheckbutton", indicatorcolor=SUPERFICIE, indicatorbackground=SUPERFICIE,
                upperbordercolor=TEXTO_SUAVE, lowerbordercolor=TEXTO_SUAVE)
    s.map("Card.TCheckbutton", background=[("active", SUPERFICIE)],
          indicatorcolor=[("selected", ACENTO), ("pressed", ACENTO_CLARO)],
          upperbordercolor=[("selected", ACENTO)], lowerbordercolor=[("selected", ACENTO)])

    # ---- botões (planos; hover discreto)
    def botao(nome, fundo, texto, borda, hover, desabilitado=None, pressionado=None):
        s.configure(nome, padding=(14, 7), background=fundo, foreground=texto, bordercolor=borda,
                    lightcolor=fundo, darkcolor=fundo, relief="flat", borderwidth=1, focuscolor=ACENTO_SUAVE)
        mapa = {"background": [("pressed", pressionado or hover), ("active", hover)],
                "bordercolor": [("active", hover if fundo == borda else borda)]}
        if desabilitado:
            mapa["background"].insert(0, ("disabled", desabilitado))
            mapa["foreground"] = [("disabled", TEXTO_SUAVE)]
        s.map(nome, **mapa)

    botao("TButton", SUPERFICIE, TEXTO, BORDA_BOTAO, "#f1f5f9", desabilitado=FUNDO)
    botao("Primario.TButton", ACENTO, SUPERFICIE, ACENTO, ACENTO_ESCURO, desabilitado="#a9c1f7")
    s.map("Primario.TButton", foreground=[("disabled", SUPERFICIE)], bordercolor=[("active", ACENTO_ESCURO)],
          background=[("disabled", "#a9c1f7"), ("pressed", ACENTO_ESCURO), ("active", ACENTO_ESCURO)])
    botao("Perigo.TButton", SUPERFICIE, VERMELHO, BORDA_BOTAO, VERMELHO_CLARO)
    botao("Ghost.TButton", SUPERFICIE, TEXTO, SUPERFICIE, FUNDO)
    s.configure("Ghost.TButton", padding=(10, 7))
    botao("Link.TButton", SUPERFICIE, ACENTO, SUPERFICIE, ACENTO_CLARO)
    botao("Nav.TButton", SUPERFICIE, TEXTO_SUAVE, SUPERFICIE, FUNDO)
    botao("NavAtivo.TButton", ACENTO_CLARO, ACENTO, ACENTO_CLARO, ACENTO_CLARO)
    s.configure("Nav.TButton", font=FONTE_NEGRITO, padding=(10, 8))
    s.configure("NavAtivo.TButton", font=FONTE_NEGRITO, padding=(10, 8))

    # ---- campos
    for campo in ("TEntry", "TCombobox"):
        s.configure(campo, padding=(8, 6), fieldbackground=SUPERFICIE, background=SUPERFICIE, bordercolor=BORDA,
                    lightcolor=BORDA, darkcolor=BORDA, insertcolor=TEXTO)
        s.map(campo, bordercolor=[("focus", ACENTO)], lightcolor=[("focus", ACENTO)], darkcolor=[("focus", ACENTO)])
    s.configure("TCombobox", arrowcolor=TEXTO_SUAVE, arrowsize=14, selectbackground=SUPERFICIE, selectforeground=TEXTO)
    s.map("TCombobox", fieldbackground=[("readonly", SUPERFICIE)], background=[("active", SUPERFICIE), ("readonly", SUPERFICIE)],
          selectbackground=[("readonly", SUPERFICIE)], selectforeground=[("readonly", TEXTO)],
          arrowcolor=[("disabled", BORDA), ("active", ACENTO)])

    # ---- navegação por abas: as abas nativas ficam ocultas (o cabeçalho tem os botões)
    s.layout("Oculto.TNotebook", [("Notebook.client", {"sticky": "nswe"})])
    s.layout("Oculto.TNotebook.Tab", [])
    s.configure("Oculto.TNotebook", borderwidth=0, background=FUNDO, tabmargins=0)

    # ---- tabelas
    s.layout("Treeview", [("Treeview.treearea", {"sticky": "nswe"})])
    s.configure("Treeview", rowheight=int(32 * ESC), background=SUPERFICIE, fieldbackground=SUPERFICIE,
                foreground=TEXTO, borderwidth=0, relief="flat")
    s.configure("Treeview.Heading", font=FONTE_PEQ_NEG, background=SUPERFICIE_ALT, foreground=TEXTO_SUAVE,
                relief="flat", padding=(10, 8), bordercolor=BORDA, lightcolor=SUPERFICIE_ALT, darkcolor=SUPERFICIE_ALT)
    s.map("Treeview.Heading", background=[("active", TRILHO)])
    s.map("Treeview", background=[("selected", ACENTO_CLARO)], foreground=[("selected", TEXTO)])

    # ---- barras de rolagem finas, sem setas
    for orient, lado in (("Vertical", "ns"), ("Horizontal", "ew")):
        nome = f"{orient}.TScrollbar"
        s.layout(nome, [(f"{orient}.Scrollbar.trough", {"sticky": lado, "children": [
            (f"{orient}.Scrollbar.thumb", {"expand": "1", "sticky": "nswe"})]})])
        s.configure(nome, background="#cbd5e1", troughcolor=SUPERFICIE, bordercolor=SUPERFICIE,
                    lightcolor="#cbd5e1", darkcolor="#cbd5e1", gripcount=0, relief="flat", width=10)
        s.map(nome, background=[("active", "#94a3b8"), ("pressed", "#94a3b8")],
              lightcolor=[("active", "#94a3b8")], darkcolor=[("active", "#94a3b8")])


# ---------------------------------------------------------------- helpers de janela/widgets
def centralizar(janela: tk.Toplevel, pai: tk.Misc, largura: int = None, altura: int = None) -> None:
    """Posiciona a janela no centro da janela principal (e opcionalmente define o tamanho)."""
    janela.update_idletasks()
    w = largura or janela.winfo_reqwidth()
    h = altura or janela.winfo_reqheight()
    topo = pai.winfo_toplevel()
    x = topo.winfo_rootx() + max(0, (topo.winfo_width() - w) // 2)
    y = topo.winfo_rooty() + max(0, (topo.winfo_height() - h) // 3)
    janela.geometry(f"{w}x{h}+{x}+{y}" if (largura or altura) else f"+{x}+{y}")


def estilizar_texto(txt: tk.Text) -> tk.Text:
    """Caixa de texto com a mesma cara dos campos (borda fina, foco azul)."""
    txt.configure(relief="flat", borderwidth=0, highlightthickness=1, highlightbackground=BORDA,
                  highlightcolor=ACENTO, bg=SUPERFICIE, fg=TEXTO, insertbackground=TEXTO, padx=8, pady=6,
                  selectbackground=ACENTO_CLARO, selectforeground=TEXTO)
    return txt


def chips(pai, itens, fundo=SUPERFICIE, por_linha=6) -> tk.Frame:
    """Etiquetas arredondadas (visualmente) para listas curtas, ex.: tecnologias."""
    quadro = tk.Frame(pai, bg=fundo)
    if not itens:
        tk.Label(quadro, text="—", bg=fundo, fg=TEXTO_SUAVE, font=FONTE).grid(row=0, column=0, sticky="w")
    for i, item in enumerate(itens):
        tk.Label(quadro, text=item, bg=ACENTO_CLARO, fg=ACENTO, font=FONTE_PEQ_NEG, padx=9, pady=2).grid(
            row=i // por_linha, column=i % por_linha, sticky="w", padx=(0, 6), pady=2)
    return quadro


def cartao_indicador(pai, rotulo: str, cor: str = ACENTO):
    """Cartão de KPI com faixa colorida à esquerda. Devolve (cartao, label_do_valor)."""
    cartao = ttk.Frame(pai, style="Card.TFrame")
    tk.Frame(cartao, bg=cor, width=4).pack(side="left", fill="y")
    interno = ttk.Frame(cartao, style="Plano.TFrame", padding=(14, 12))
    interno.pack(side="left", fill="both", expand=True)
    ttk.Label(interno, text=rotulo, style="CardMuted.TLabel").pack(anchor="w")
    valor = ttk.Label(interno, text="—", style="Valor.TLabel")
    valor.pack(anchor="w", pady=(2, 0))
    return cartao, valor


# ---------------------------------------------------------------- tabelas
def _repintar(tree: ttk.Treeview) -> None:
    """Zebra + destaque da seleção feitos por 'tags' (funciona igual em todas as versões do Tk)."""
    sel = set(tree.selection())
    for i, iid in enumerate(tree.get_children()):
        tree.item(iid, tags=("sel" if iid in sel else ("par" if i % 2 == 0 else "impar"),))


def inserir(tree: ttk.Treeview, valores, iid=None):
    """Insere uma linha mantendo a zebra. Use no lugar de tree.insert('', 'end', ...)."""
    i = len(tree.get_children())
    extra = {"iid": iid} if iid is not None else {}
    return tree.insert("", "end", values=valores, tags=("par" if i % 2 == 0 else "impar",), **extra)


def criar_tree(pai, colunas, larguras=None, altura=10, selectmode="extended"):
    """Treeview com barra de rolagem. colunas = [(chave, titulo, largura, ancora)]"""
    frame = ttk.Frame(pai, style="Plano.TFrame")
    tree = ttk.Treeview(
        frame, columns=[c[0] for c in colunas], show="headings", height=altura, selectmode=selectmode
    )
    for chave, titulo, largura, ancora in colunas:
        tree.heading(chave, text=titulo, anchor=ancora)
        tree.column(chave, width=largura, anchor=ancora, minwidth=40)
    tree.tag_configure("par", background=SUPERFICIE)
    tree.tag_configure("impar", background=SUPERFICIE_ALT)
    tree.tag_configure("sel", background=ACENTO_CLARO, foreground=TEXTO)
    tree.bind("<<TreeviewSelect>>", lambda _e: _repintar(tree), add="+")
    sb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=sb.set)
    tree.pack(side="left", fill="both", expand=True)
    sb.pack(side="right", fill="y")
    return frame, tree


# ---------------------------------------------------------------- gráficos (Canvas)
def _vazio(canvas, texto="Sem dados para exibir"):
    canvas.create_text(
        canvas.winfo_width() / 2, canvas.winfo_height() / 2, text=texto, fill=TEXTO_SUAVE, font=FONTE
    )


def _escala(vmax):
    """Teto e passo 'redondos' (1, 2, 5, 10 × 10ⁿ) para o eixo de contagens inteiras."""
    if vmax <= 0:
        return 4, 1
    bruto = vmax / 4
    base = 10 ** math.floor(math.log10(bruto))
    passo = next(m * base for m in (1, 2, 5, 10) if m * base >= bruto)
    passo = max(1, int(round(passo)))
    return math.ceil(vmax / passo) * passo, passo


def grafico_barras(canvas: tk.Canvas, dados, cor=ACENTO):
    """dados = [(rótulo, valor)]. Ranking em barras horizontais (o líder em destaque)."""
    canvas.delete("all")
    w, h = canvas.winfo_width(), canvas.winfo_height()
    if w < 50 or h < 50:
        return
    if not dados:
        return _vazio(canvas)
    fonte = tkfont.Font(font=FONTE_PEQ)
    larg_rot = min(max(fonte.measure(r) for r, _ in dados), 130)
    x0, x1 = 12 + larg_rot + 14, w - 52
    mt = mb = 6
    linha = (h - mt - mb) / len(dados)
    espessura = max(6, min(14, linha * 0.5))
    vmax = max(v for _, v in dados) or 1
    for i, (rotulo, valor) in enumerate(dados):
        cy = mt + linha * (i + 0.5)
        txt = rotulo
        while len(txt) > 1 and fonte.measure(txt) > larg_rot:
            txt = txt[:-2] + "…"
        canvas.create_text(12, cy, text=txt, anchor="w", fill=TEXTO, font=FONTE_PEQ)
        canvas.create_line(x0, cy, x1, cy, fill=TRILHO, width=espessura, capstyle="round")
        if valor > 0:
            xf = max(x0 + 1, x0 + (x1 - x0) * valor / vmax)
            canvas.create_line(x0, cy, xf, cy, fill=cor if i == 0 else ACENTO_SUAVE, width=espessura, capstyle="round")
        canvas.create_text(x1 + 14, cy, text=str(valor), anchor="w", fill=TEXTO, font=FONTE_PEQ_NEG)


def grafico_linha(canvas: tk.Canvas, dados, cor=VERDE):
    """dados = [(rótulo, valor)]. Linha com área suave e pontos."""
    canvas.delete("all")
    w, h = canvas.winfo_width(), canvas.winfo_height()
    if w < 50 or h < 50:
        return
    if not dados:
        return _vazio(canvas)
    ml, mr, mt, mb = 40, 24, 26, 34
    topo, passo = _escala(max(v for _, v in dados))
    area_h = h - mt - mb

    def y_de(v):
        return h - mb - area_h * v / topo

    n = len(dados)
    pts = []
    for i, (rotulo, valor) in enumerate(dados):
        x = ml + 16 + (w - ml - mr - 32) * i / (n - 1) if n > 1 else (ml + w - mr) / 2
        pts.append((x, y_de(valor), rotulo, valor))
    if n > 1:
        canvas.create_polygon(pts[0][0], h - mb, *[c for p in pts for c in p[:2]], pts[-1][0], h - mb,
                              fill=VERDE_CLARO, outline="")
    for t in range(0, topo + 1, passo):
        y = y_de(t)
        canvas.create_line(ml, y, w - mr, y, fill=TRILHO if t else BORDA)
        canvas.create_text(ml - 8, y, text=str(t), anchor="e", fill=TEXTO_SUAVE, font=FONTE_PEQ)
    if n > 1:
        canvas.create_line(*[c for p in pts for c in p[:2]], fill=cor, width=3, joinstyle="round")
    for x, y, rotulo, valor in pts:
        canvas.create_oval(x - 5, y - 5, x + 5, y + 5, fill=SUPERFICIE, outline=cor, width=2)
        canvas.create_text(x, y - 16, text=str(valor), fill=TEXTO, font=FONTE_PEQ_NEG)
        canvas.create_text(x, h - mb + 16, text=rotulo, fill=TEXTO_SUAVE, font=FONTE_PEQ)


def canvas_grafico(pai, funcao, altura=240):
    """Canvas que se redesenha sozinho ao redimensionar. Use .dados = [...] e .redesenhar()."""
    c = tk.Canvas(pai, height=altura, bg=SUPERFICIE, highlightthickness=0)
    c.dados = []
    c.redesenhar = lambda: funcao(c, c.dados)
    c.bind("<Configure>", lambda _e: c.redesenhar())
    return c
