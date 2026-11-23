"""Aba Relatório de Informações."""
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from core import formatadores as fmt
from core.servicos import exportar_csv
from . import tema


class AbaRelatorio(ttk.Frame):
    def __init__(self, pai, servico):
        super().__init__(pai, padding=(24, 20))
        self.s = servico
        topo = ttk.Frame(self)
        topo.pack(fill="x")
        bloco = ttk.Frame(topo)
        bloco.pack(side="left")
        ttk.Label(bloco, text="Relatório de Informações", style="Titulo.TLabel").pack(anchor="w")
        ttk.Label(bloco, text="Resumo consolidado de todas as vagas cadastradas.", style="Muted.TLabel").pack(anchor="w")
        ttk.Button(topo, text="Exportar CSV", command=self.exportar_csv).pack(side="right", anchor="s")
        ttk.Button(topo, text="Salvar TXT", command=self.salvar_txt).pack(side="right", anchor="s", padx=8)
        ttk.Button(topo, text="⟳ Atualizar", style="Primario.TButton", command=self.atualizar).pack(side="right", anchor="s")

        quadro = ttk.Frame(self, style="Card.TFrame", padding=1)
        quadro.pack(fill="both", expand=True, pady=(16, 0))
        self.txt = tk.Text(quadro, wrap="none", font=(tema.FAMILIA_MONO, 10), relief="flat", borderwidth=0,
                           highlightthickness=0, bg=tema.SUPERFICIE, fg=tema.TEXTO, padx=24, pady=16,
                           spacing1=2, spacing3=2, selectbackground=tema.ACENTO_CLARO, selectforeground=tema.TEXTO)
        self.txt.tag_configure("h1", font=(tema.FAMILIA_MONO, 14, "bold"), foreground=tema.TEXTO, spacing3=4)
        self.txt.tag_configure("h2", font=(tema.FAMILIA_MONO, 10, "bold"), foreground=tema.ACENTO, spacing1=6)
        self.txt.tag_configure("regua", foreground=tema.BORDA)
        self.txt.tag_configure("vazio", foreground=tema.TEXTO_SUAVE)
        sb = ttk.Scrollbar(quadro, command=self.txt.yview)
        self.txt.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.txt.pack(side="left", fill="both", expand=True)
        self.atualizar()

    def atualizar(self):
        self.txt.config(state="normal")
        self.txt.delete("1.0", "end")
        linhas = self.s.relatorio_texto().split("\n")
        for i, linha in enumerate(linhas):
            solta = linha.strip()
            if i == 0:
                tag = "h1"
            elif solta and set(solta) <= {"-", "="}:
                tag = "regua"
            elif i + 1 < len(linhas) and linhas[i + 1].startswith("---"):
                tag = "h2"
            elif solta == "(sem dados)":
                tag = "vazio"
            else:
                tag = None
            self.txt.insert("end", linha + ("\n" if i < len(linhas) - 1 else ""), tag or ())
        self.txt.config(state="disabled")

    def salvar_txt(self):
        caminho = filedialog.asksaveasfilename(parent=self, defaultextension=".txt", initialfile="relatorio-vagas.txt",
                                               filetypes=[("Texto", "*.txt")])
        if not caminho:
            return
        try:
            with open(caminho, "w", encoding="utf-8") as f:
                f.write(self.s.relatorio_texto())
        except OSError as e:
            return messagebox.showerror("Erro ao salvar", str(e), parent=self)
        messagebox.showinfo("Relatório salvo", caminho, parent=self)

    def exportar_csv(self):
        caminho = filedialog.asksaveasfilename(parent=self, defaultextension=".csv", initialfile="relatorio-vagas.csv",
                                               filetypes=[("CSV", "*.csv")])
        if not caminho:
            return
        r = self.s.relatorio()
        linhas = [["resumo", "total_vagas", r["total_vagas"]], ["resumo", "empresas", r["total_empresas"]],
                  ["resumo", "salario_medio", r["salario_medio"]], ["resumo", "percentual_remoto", r["percentual_remoto"]]]
        linhas += [["senioridade", fmt.formatar_senioridade(k), q] for k, q in r["por_senioridade"]]
        linhas += [["modalidade", fmt.formatar_modalidade(k), q] for k, q in r["por_modalidade"]]
        linhas += [["estado", k, q] for k, q in r["por_estado"]]
        linhas += [["empresa", k, q] for k, q in r["top_empresas"]]
        linhas += [["tecnologia", k, q] for k, q in r["top_tecnologias"]]
        linhas += [["salario", f"{x['tecnologia']} / {fmt.formatar_senioridade(x['senioridade'])}", x["salario_medio"]]
                   for x in r["salarios"]]
        try:
            exportar_csv(caminho, ["secao", "item", "valor"], linhas)
        except OSError as e:
            return messagebox.showerror("Erro ao salvar", str(e), parent=self)
        messagebox.showinfo("Exportação concluída", caminho, parent=self)
