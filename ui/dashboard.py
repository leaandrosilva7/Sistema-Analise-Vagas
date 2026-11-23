"""Aba Dashboard analítico (UC05–UC08, UC17, UC18)."""
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from core import formatadores as fmt
from core.servicos import exportar_csv
from . import tema


MESES = ("jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez")


def _rotulo_mes(periodo: str) -> str:
    """'2026-06' -> 'jun/26' (qualquer outro formato volta como veio)."""
    try:
        ano, mes = periodo.split("-")[:2]
        return f"{MESES[int(mes) - 1]}/{ano[-2:]}"
    except (ValueError, IndexError, AttributeError):
        return str(periodo)


class AbaDashboard(ttk.Frame):
    def __init__(self, pai, servico):
        super().__init__(pai, padding=(24, 16))
        self.s = servico
        self.techs, self.tend, self.sal = [], [], []

        topo = ttk.Frame(self)
        topo.pack(fill="x")
        bloco = ttk.Frame(topo)
        bloco.pack(side="left")
        ttk.Label(bloco, text="Dashboard Analítico", style="Titulo.TLabel").pack(anchor="w")
        ttk.Label(bloco, text="Indicadores do mercado de tecnologia.", style="Muted.TLabel").pack(anchor="w")
        ttk.Button(topo, text="Exportar análise (CSV)", style="Primario.TButton",
                   command=self.exportar).pack(side="right", anchor="s")
        ttk.Button(topo, text="⟳ Atualizar", command=self.atualizar).pack(side="right", anchor="s", padx=8)

        # ---- cartões
        cards = ttk.Frame(self)
        cards.pack(fill="x", pady=(12, 12))
        self.valores = {}
        indicadores = [("total_vagas", "TOTAL DE VAGAS", tema.ACENTO), ("salario_medio", "SALÁRIO MÉDIO", tema.VERDE),
                       ("percentual_remoto", "TRABALHO REMOTO", "#f59e0b"), ("skill_top", "TECNOLOGIA TOP", "#8b5cf6")]
        for i, (chave, rotulo, cor) in enumerate(indicadores):
            c, self.valores[chave] = tema.cartao_indicador(cards, rotulo, cor)
            c.grid(row=0, column=i, sticky="ew", padx=(0 if i == 0 else 12, 0))
            cards.columnconfigure(i, weight=1, uniform="c")

        # ---- gráficos
        graf = ttk.Frame(self)
        graf.pack(fill="both", expand=True)
        graf.rowconfigure(0, weight=1)
        graf.columnconfigure((0, 1), weight=1, uniform="g")
        g1 = ttk.Frame(graf, style="Card.TFrame", padding=14)
        g1.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        cab = ttk.Frame(g1, style="Plano.TFrame")
        cab.pack(fill="x")
        ttk.Label(cab, text="Tecnologias mais citadas", style="Sub.TLabel").pack(side="left")
        self.var_periodo = tk.StringVar(value="Todos")
        self.cb_periodo = ttk.Combobox(cab, textvariable=self.var_periodo, state="readonly", width=10)
        self.cb_periodo.pack(side="right")
        self.cb_periodo.bind("<<ComboboxSelected>>", lambda _e: self.desenhar_techs())
        self.cv_techs = tema.canvas_grafico(g1, tema.grafico_barras, 150)
        self.cv_techs.pack(fill="both", expand=True, pady=(6, 0))

        g2 = ttk.Frame(graf, style="Card.TFrame", padding=14)
        g2.grid(row=0, column=1, sticky="nsew")
        ttk.Label(g2, text="Vagas publicadas por mês", style="Sub.TLabel").pack(anchor="w")
        self.cv_tend = tema.canvas_grafico(g2, tema.grafico_linha, 150)
        self.cv_tend.pack(fill="both", expand=True, pady=(6, 0))

        # ---- tabelas
        tabs = ttk.Frame(self)
        tabs.pack(fill="both", expand=True, pady=(12, 0))
        tabs.columnconfigure((0, 1), weight=1, uniform="t")
        tabs.rowconfigure(0, weight=1)
        t1 = ttk.Frame(tabs, style="Card.TFrame", padding=14)
        t1.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        ttk.Label(t1, text="Salários por tecnologia (últimos 30 dias)", style="Sub.TLabel").pack(anchor="w", pady=(0, 6))
        f1, self.tree_sal = tema.criar_tree(t1, [
            ("t", "Tecnologia", 110, "w"), ("n", "Senioridade", 80, "w"),
            ("m", "Salário médio", 110, "e"), ("q", "Vagas", 50, "e")], altura=2)
        f1.pack(fill="both", expand=True)
        t2 = ttk.Frame(tabs, style="Card.TFrame", padding=14)
        t2.grid(row=0, column=1, sticky="nsew")
        ttk.Label(t2, text="Vagas mais recentes", style="Sub.TLabel").pack(anchor="w", pady=(0, 6))
        f2, self.tree_rec = tema.criar_tree(t2, [
            ("t", "Título", 200, "w"), ("e", "Empresa", 100, "w"), ("d", "Data", 80, "center")], altura=2)
        f2.pack(fill="both", expand=True)

        self.atualizar()

    def atualizar(self):
        m = self.s.metricas()
        self.valores["total_vagas"].config(text=str(m["total_vagas"]))
        self.valores["salario_medio"].config(text=fmt.formatar_moeda(m["salario_medio"]) if m["salario_medio"] else "Não informado")
        self.valores["percentual_remoto"].config(text=f"{m['percentual_remoto']}%")
        self.valores["skill_top"].config(text=m["skill_top"])

        self.techs = self.s.tecnologias_demandadas()
        self.tend = self.s.tendencias()
        self.sal = self.s.estatisticas_salariais(periodo=30)

        periodos = sorted({t["periodo"] for t in self.techs})
        self.cb_periodo.config(values=["Todos"] + periodos)
        if self.var_periodo.get() not in ["Todos"] + periodos:
            self.var_periodo.set("Todos")
        self.desenhar_techs()
        self.cv_tend.dados = [(_rotulo_mes(t["periodo"]), t["total_vagas"]) for t in self.tend][-12:]
        self.cv_tend.redesenhar()

        self.tree_sal.delete(*self.tree_sal.get_children())
        for s in sorted(self.sal, key=lambda x: -x["salario_medio"])[:40]:
            tema.inserir(self.tree_sal, (s["tecnologia"], fmt.formatar_senioridade(s["senioridade"]),
                                         fmt.formatar_moeda(s["salario_medio"]), s["total_vagas"]))
        self.tree_rec.delete(*self.tree_rec.get_children())
        for v in self.s.vagas_recentes(10):
            tema.inserir(self.tree_rec, (v["titulo"], v["empresa"], fmt.formatar_data(v["data_publicacao"]) or "—"))

    def desenhar_techs(self):
        per = self.var_periodo.get()
        contagem = {}
        for t in self.techs:
            if per == "Todos" or t["periodo"] == per:
                contagem[t["tecnologia"]] = contagem.get(t["tecnologia"], 0) + t["total_vagas"]
        top = sorted(contagem.items(), key=lambda kv: (-kv[1], kv[0]))[:8]
        self.cv_techs.dados = top
        self.cv_techs.redesenhar()

    def exportar(self):
        caminho = filedialog.asksaveasfilename(parent=self, defaultextension=".csv", initialfile="analise-mercado.csv",
                                               filetypes=[("CSV", "*.csv")])
        if not caminho:
            return
        linhas = (
            [["tecnologia", t["tecnologia"], t["periodo"], t["total_vagas"]] for t in self.techs]
            + [["tendencia", t["periodo"], t["periodo"], t["total_vagas"]] for t in self.tend]
            + [["salario", t["tecnologia"], fmt.formatar_senioridade(t["senioridade"]), t["salario_medio"]] for t in self.sal]
        )
        try:
            exportar_csv(caminho, ["tipo", "categoria", "periodo", "valor"], linhas)
        except OSError as e:
            return messagebox.showerror("Erro ao salvar", str(e), parent=self)
        messagebox.showinfo("Exportação concluída", f"Análise salva em:\n{caminho}", parent=self)
