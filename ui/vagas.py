"""Aba de vagas (consulta + CRUD), formulário, detalhes e comparação."""
import tkinter as tk
import webbrowser
from tkinter import filedialog, messagebox, ttk

from core import formatadores as fmt
from core.servicos import ErroValidacao, exportar_csv
from . import tema

POR_PAGINA = 30
OPCOES_SENIORIDADE = [("", "Todas")] + [(k, v) for k, v in fmt.SENIORIDADES.items()]
OPCOES_MODALIDADE = [("", "Todas")] + [(k, v) for k, v in fmt.MODALIDADES.items()]
OPCOES_PERIODO = [("", "Todos"), ("7", "Últimos 7 dias"), ("30", "Últimos 30 dias"),
                  ("90", "Últimos 90 dias"), ("365", "Último ano")]


def _combo(pai, opcoes, largura=14, inicial=0):
    """Combobox que mostra rótulos e devolve a chave via .chave()."""
    var = tk.StringVar(value=opcoes[inicial][1])
    cb = ttk.Combobox(pai, textvariable=var, values=[r for _, r in opcoes], state="readonly", width=largura)
    cb.chave = lambda: next((k for k, r in opcoes if r == var.get()), "")
    cb.definir = lambda chave: var.set(next((r for k, r in opcoes if k == chave), opcoes[0][1]))
    return cb


class AbaVagas(ttk.Frame):
    def __init__(self, pai, servico, ao_alterar=lambda: None):
        super().__init__(pai, padding=(24, 20))
        self.s = servico
        self.ao_alterar = ao_alterar
        self.pagina = 1
        self.total = 0
        self.vagas = {}

        topo = ttk.Frame(self)
        topo.pack(fill="x")
        bloco = ttk.Frame(topo)
        bloco.pack(side="left")
        ttk.Label(bloco, text="Vagas", style="Titulo.TLabel").pack(anchor="w")
        ttk.Label(bloco, text="Pesquise, inclua, altere, remova e compare oportunidades.",
                  style="Muted.TLabel").pack(anchor="w")
        ttk.Button(topo, text="＋ Nova vaga", style="Primario.TButton", command=self.nova).pack(side="right", anchor="s")
        ttk.Button(topo, text="Exportar CSV", command=self.exportar).pack(side="right", anchor="s", padx=8)

        # ---- filtros
        box = ttk.Frame(self, style="Card.TFrame", padding=(14, 12))
        box.pack(fill="x", pady=(16, 12))
        self.v_texto, self.v_tec, self.v_cid = tk.StringVar(), tk.StringVar(), tk.StringVar()
        campos = [("Título ou empresa", self.v_texto, 3), ("Tecnologia", self.v_tec, 2),
                  ("Localização", self.v_cid, 2)]
        for i, (rot, var, peso) in enumerate(campos):
            ttk.Label(box, text=rot, style="Campo.TLabel").grid(row=0, column=i, sticky="w", padx=4)
            e = ttk.Entry(box, textvariable=var, width=18 if peso == 3 else 10)
            e.grid(row=1, column=i, padx=4, sticky="ew", pady=(3, 0))
            e.bind("<Return>", lambda _e: self.buscar())
            box.columnconfigure(i, weight=peso)
        self.cb_sen = _combo(box, OPCOES_SENIORIDADE, 10)
        self.cb_mod = _combo(box, OPCOES_MODALIDADE, 10)
        self.cb_per = _combo(box, OPCOES_PERIODO, 13)
        for i, (rot, cb) in enumerate([("Senioridade", self.cb_sen), ("Modalidade", self.cb_mod), ("Período", self.cb_per)], start=3):
            ttk.Label(box, text=rot, style="Campo.TLabel").grid(row=0, column=i, sticky="w", padx=4)
            cb.grid(row=1, column=i, padx=4, sticky="ew", pady=(3, 0))
            box.columnconfigure(i, weight=1)
        ttk.Button(box, text="Buscar", style="Primario.TButton", command=self.buscar).grid(row=1, column=6, padx=(12, 4), sticky="s")
        ttk.Button(box, text="Limpar", command=self.limpar).grid(row=1, column=7, padx=4, sticky="s")

        # ---- ações sobre a seleção
        acoes = ttk.Frame(self)
        acoes.pack(fill="x", pady=(0, 8))
        ttk.Button(acoes, text="Detalhes", command=self.detalhes).pack(side="left")
        ttk.Button(acoes, text="Editar", command=self.editar).pack(side="left", padx=6)
        ttk.Button(acoes, text="Comparar selecionadas", command=self.comparar).pack(side="left")
        ttk.Button(acoes, text="Abrir link", command=self.abrir_link).pack(side="left", padx=6)
        ttk.Button(acoes, text="Excluir", style="Perigo.TButton", command=self.excluir).pack(side="right")

        # ---- tabela
        colunas = [("id", "ID", 44, "e"), ("titulo", "Título", 200, "w"), ("empresa", "Empresa", 110, "w"),
                   ("local", "Local", 130, "w"), ("senior", "Senioridade", 85, "w"),
                   ("modal", "Modalidade", 85, "w"), ("salario", "Faixa salarial", 190, "w"),
                   ("data", "Publicação", 85, "center")]
        moldura = ttk.Frame(self, style="Card.TFrame", padding=1)
        moldura.pack(fill="both", expand=True)
        frame, self.tree = tema.criar_tree(moldura, colunas, altura=6)
        frame.pack(fill="both", expand=True)
        self.tree.bind("<Double-1>", lambda _e: self.detalhes())
        self.tree.bind("<Return>", lambda _e: self.detalhes())
        self.tree.bind("<Delete>", lambda _e: self.excluir())

        # ---- paginação
        rod = ttk.Frame(self)
        rod.pack(fill="x", pady=(10, 0))
        self.lbl_info = ttk.Label(rod, text="", style="Muted.TLabel")
        self.lbl_info.pack(side="left")
        self.btn_prox = ttk.Button(rod, text="Próxima ›", command=lambda: self.ir_pagina(self.pagina + 1))
        self.btn_prox.pack(side="right")
        self.lbl_pag = ttk.Label(rod, text="")
        self.lbl_pag.pack(side="right", padx=8)
        self.btn_ant = ttk.Button(rod, text="‹ Anterior", command=lambda: self.ir_pagina(self.pagina - 1))
        self.btn_ant.pack(side="right")

        self.carregar()

    # ----- consulta
    def filtros(self) -> dict:
        return {"texto": self.v_texto.get(), "tecnologia": self.v_tec.get(), "cidade": self.v_cid.get(),
                "senioridade": self.cb_sen.chave(), "modalidade": self.cb_mod.chave(),
                "periodo": self.cb_per.chave()}

    def buscar(self):
        self.pagina = 1
        self.carregar()

    def limpar(self):
        for v in (self.v_texto, self.v_tec, self.v_cid):
            v.set("")
        for cb in (self.cb_sen, self.cb_mod, self.cb_per):
            cb.current(0)
        self.buscar()

    def ir_pagina(self, n):
        self.pagina = n
        self.carregar()

    def carregar(self):
        try:
            vagas, self.total = self.s.listar_vagas(self.filtros(), self.pagina, POR_PAGINA)
        except ErroValidacao as e:
            messagebox.showwarning("Filtro inválido", str(e), parent=self)
            return
        paginas = max(1, -(-self.total // POR_PAGINA))
        if self.pagina > paginas:  # ex.: removeu o último item da última página
            self.pagina = paginas
            return self.carregar()
        self.tree.delete(*self.tree.get_children())
        self.vagas = {v["id"]: v for v in vagas}
        for v in vagas:
            tema.inserir(self.tree, (
                v["id"], v["titulo"], v["empresa"],
                v["localizacao"] or ", ".join(x for x in (v["cidade"], v["estado"]) if x) or "—",
                fmt.formatar_senioridade(v["senioridade"]), fmt.formatar_modalidade(v["modalidade"]),
                fmt.formatar_faixa(v["salario_min"], v["salario_max"], v["moeda"]),
                fmt.formatar_data(v["data_publicacao"]) or "—"), iid=str(v["id"]))
        self.lbl_info.config(text=f"{self.total} vaga(s) encontrada(s)" if self.total else
                             "Nenhuma vaga encontrada. Use “Nova vaga” ou Arquivo ▸ Importar.")
        self.lbl_pag.config(text=f"Página {self.pagina} de {paginas}")
        self.btn_ant.state(["!disabled"] if self.pagina > 1 else ["disabled"])
        self.btn_prox.state(["!disabled"] if self.pagina < paginas else ["disabled"])

    def _ids(self) -> list:
        return [int(i) for i in self.tree.selection()]

    def _um(self):
        ids = self._ids()
        if not ids:
            messagebox.showinfo("Selecione uma vaga", "Clique em uma vaga da lista primeiro.", parent=self)
            return None
        return ids[0]

    # ----- CRUD
    def nova(self):
        FormularioVaga(self, self.s, None, self._salvou)

    def editar(self):
        vid = self._um()
        if vid:
            FormularioVaga(self, self.s, vid, self._salvou)

    def excluir(self):
        ids = self._ids()
        if not ids:
            return messagebox.showinfo("Selecione uma vaga", "Clique em uma ou mais vagas da lista.", parent=self)
        if not messagebox.askyesno("Confirmar exclusão", f"Excluir {len(ids)} vaga(s) selecionada(s)?\n"
                                   "Esta ação não pode ser desfeita.", icon="warning", parent=self):
            return
        self.s.excluir_vagas(ids)
        self._salvou()

    def _salvou(self):
        self.carregar()
        self.ao_alterar()

    def detalhes(self):
        vid = self._um()
        if vid:
            DetalhesVaga(self, self.s, vid)

    def comparar(self):
        ids = self._ids()
        try:
            vagas = self.s.comparar_vagas(ids)
        except ErroValidacao as e:
            return messagebox.showinfo("Comparar vagas", str(e), parent=self)
        ComparacaoVagas(self, vagas)

    def abrir_link(self):
        vid = self._um()
        if not vid:
            return
        url = self.vagas[vid].get("url_original")
        if url:
            webbrowser.open(url)
        else:
            messagebox.showinfo("Sem link", "Esta vaga não possui link original.", parent=self)

    def exportar(self):
        caminho = filedialog.asksaveasfilename(parent=self, defaultextension=".csv", initialfile="vagas.csv",
                                               filetypes=[("CSV", "*.csv")])
        if not caminho:
            return
        todas, pag = [], 1
        while True:
            lote, total = self.s.listar_vagas(self.filtros(), pag, 500)
            todas += lote
            if len(todas) >= total or not lote:
                break
            pag += 1
        cab = ["id", "titulo", "empresa", "cidade", "estado", "senioridade", "modalidade",
               "salario_min", "salario_max", "moeda", "tecnologias", "data_publicacao", "url_original"]
        linhas = [[v["id"], v["titulo"], v["empresa"], v["cidade"], v["estado"],
                   fmt.formatar_senioridade(v["senioridade"]), fmt.formatar_modalidade(v["modalidade"]),
                   v["salario_min"], v["salario_max"], v["moeda"], ", ".join(v["skills"]),
                   v["data_publicacao"], v["url_original"]] for v in todas]
        try:
            exportar_csv(caminho, cab, linhas)
        except OSError as e:
            return messagebox.showerror("Erro ao salvar", str(e), parent=self)
        messagebox.showinfo("Exportação concluída", f"{len(linhas)} vaga(s) salvas em:\n{caminho}", parent=self)


class FormularioVaga(tk.Toplevel):
    """Janela de inclusão (vaga_id=None) ou alteração de uma vaga."""

    def __init__(self, pai, servico, vaga_id, ao_salvar):
        super().__init__(pai)
        self.s, self.vaga_id, self.ao_salvar = servico, vaga_id, ao_salvar
        self.title("Nova vaga" if vaga_id is None else f"Editar vaga #{vaga_id}")
        self.configure(bg=tema.SUPERFICIE)
        self.transient(pai.winfo_toplevel())
        self.resizable(False, False)

        v = servico.obter_vaga(vaga_id) if vaga_id else {}
        corpo = ttk.Frame(self, style="Plano.TFrame", padding=24)
        corpo.pack(fill="both", expand=True)
        corpo.columnconfigure((0, 1), weight=1)
        self.vars = {}

        def campo(row, col, chave, rotulo, largura=28, valor=None):
            ttk.Label(corpo, text=rotulo, style="Campo.TLabel").grid(row=row * 2, column=col, sticky="w", padx=6)
            var = tk.StringVar(value="" if (valor if valor is not None else v.get(chave)) is None
                               else str(valor if valor is not None else v.get(chave)))
            ttk.Entry(corpo, textvariable=var, width=largura).grid(row=row * 2 + 1, column=col, padx=6, pady=(3, 10), sticky="ew")
            self.vars[chave] = var

        campo(0, 0, "titulo", "Título *", 40)
        campo(0, 1, "empresa", "Empresa *")
        campo(1, 0, "cidade", "Cidade")
        campo(1, 1, "estado", "Estado (UF)")
        # combos
        ttk.Label(corpo, text="Modalidade", style="Campo.TLabel").grid(row=4, column=0, sticky="w", padx=6)
        self.cb_mod = _combo(corpo, OPCOES_MODALIDADE[1:], 20, inicial=3)
        self.cb_mod.definir(fmt.normalizar_modalidade(v.get("modalidade")))
        self.cb_mod.grid(row=5, column=0, padx=6, pady=(3, 10), sticky="ew")
        ttk.Label(corpo, text="Senioridade", style="Campo.TLabel").grid(row=4, column=1, sticky="w", padx=6)
        self.cb_sen = _combo(corpo, OPCOES_SENIORIDADE[1:], 20, inicial=5)
        self.cb_sen.definir(fmt.normalizar_senioridade(v.get("senioridade")))
        self.cb_sen.grid(row=5, column=1, padx=6, pady=(3, 10), sticky="ew")
        campo(3, 0, "salario_min", "Salário mínimo (R$)", 18)
        campo(3, 1, "salario_max", "Salário máximo (R$)", 18)
        campo(4, 0, "data_publicacao", "Data de publicação (DD/MM/AAAA)", 18,
              fmt.formatar_data(v.get("data_publicacao")) if v else fmt.formatar_data(fmt.hoje()))
        campo(4, 1, "moeda", "Moeda", 8, v.get("moeda") or "BRL")
        campo(5, 0, "url_original", "Link original (https://…)", 40)
        campo(5, 1, "skills", "Tecnologias (separe por vírgula)", 28,
              ", ".join(v.get("skills", [])) if v else "")
        if v:
            for k in ("salario_min", "salario_max"):
                if v.get(k) is not None:
                    self.vars[k].set(f"{v[k]:.2f}".rstrip("0").rstrip("."))
        ttk.Label(corpo, text="Descrição", style="Campo.TLabel").grid(row=12, column=0, sticky="w", padx=6)
        self.txt = tema.estilizar_texto(tk.Text(corpo, width=74, height=6, wrap="word", font=tema.FONTE))
        self.txt.grid(row=13, column=0, columnspan=2, padx=6, pady=(3, 10), sticky="ew")
        self.txt.insert("1.0", v.get("descricao") or "")
        self._extra = {k: v.get(k) for k in ("fonte", "id_externo", "localizacao", "pais", "url_normalizada",
                                              "salario_estimado", "data_coleta")}

        self.lbl_erro = ttk.Label(corpo, text="", style="ErroCard.TLabel", wraplength=560)
        self.lbl_erro.grid(row=14, column=0, columnspan=2, sticky="w", padx=6)
        bt = ttk.Frame(corpo, style="Plano.TFrame")
        bt.grid(row=15, column=0, columnspan=2, sticky="e", pady=(10, 0), padx=6)
        ttk.Button(bt, text="Cancelar", command=self.destroy).pack(side="left", padx=4)
        ttk.Button(bt, text="Salvar", style="Primario.TButton", command=self.salvar).pack(side="left")

        self.bind("<Escape>", lambda _e: self.destroy())
        tema.centralizar(self, pai)
        self.grab_set()
        self.focus_set()

    def salvar(self):
        dados = {k: var.get() for k, var in self.vars.items() if k != "skills"}
        dados.update(self._extra)
        dados["modalidade"] = self.cb_mod.chave()
        dados["senioridade"] = self.cb_sen.chave()
        dados["descricao"] = self.txt.get("1.0", "end").strip()
        if not dados.get("localizacao") or self.vaga_id is None:
            dados["localizacao"] = ", ".join(x for x in (dados["cidade"].strip(), dados["estado"].strip()) if x)
        try:
            if self.vaga_id is None:
                self.s.criar_vaga(dados, self.vars["skills"].get())
            else:
                self.s.atualizar_vaga(self.vaga_id, dados, self.vars["skills"].get())
        except ErroValidacao as e:
            self.lbl_erro.config(text=str(e))
            return
        self.ao_salvar()
        self.destroy()


class DetalhesVaga(tk.Toplevel):
    def __init__(self, pai, servico, vaga_id):
        super().__init__(pai)
        self.configure(bg=tema.FUNDO)
        try:
            dados = servico.detalhes_vaga(vaga_id)
        except ErroValidacao as e:
            messagebox.showerror("Erro", str(e), parent=pai)
            self.destroy()
            return
        v = dados["vaga"]
        self.title(f"Vaga #{v['id']} — {v['titulo']}")
        corpo = ttk.Frame(self, padding=24)
        corpo.pack(fill="both", expand=True)
        ttk.Label(corpo, text=v["titulo"], style="Titulo.TLabel", wraplength=700).pack(anchor="w")
        ttk.Label(corpo, text=v["empresa"], style="Muted.TLabel").pack(anchor="w", pady=(0, 14))

        info = ttk.Frame(corpo, style="Card.TFrame", padding=16)
        info.pack(fill="x")
        local = v["localizacao"] or ", ".join(x for x in (v["cidade"], v["estado"]) if x) or "Não informado"
        linhas = [("Local", local), ("Modalidade", fmt.formatar_modalidade(v["modalidade"])),
                  ("Senioridade", fmt.formatar_senioridade(v["senioridade"])),
                  ("Faixa salarial", fmt.formatar_faixa(v["salario_min"], v["salario_max"], v["moeda"])),
                  ("Publicação", fmt.formatar_data(v["data_publicacao"]) or "—"),
                  ("Fonte", v["fonte"] or "Cadastro manual"), ("Link", v["url_original"] or "—")]
        linhas.insert(5, ("Tecnologias", None))
        for i, (r, t) in enumerate(linhas):
            ttk.Label(info, text=r, style="CardMuted.TLabel").grid(row=i, column=0, sticky="nw", padx=(0, 18), pady=4)
            if t is None:
                tema.chips(info, v["skills"]).grid(row=i, column=1, sticky="w")
            else:
                ttk.Label(info, text=t, style="Card.TLabel", wraplength=560, justify="left").grid(row=i, column=1, sticky="w")

        ttk.Label(corpo, text="Descrição", style="SubFundo.TLabel").pack(anchor="w", pady=(16, 4))
        txt = tema.estilizar_texto(tk.Text(corpo, height=7, wrap="word", font=tema.FONTE))
        txt.insert("1.0", v["descricao"] or "Sem descrição.")
        txt.config(state="disabled")
        txt.pack(fill="x")

        ttk.Label(corpo, text="Salários de mercado relacionados (mesma senioridade e tecnologia)",
                  style="SubFundo.TLabel").pack(anchor="w", pady=(16, 4))
        moldura = ttk.Frame(corpo, style="Card.TFrame", padding=1)
        moldura.pack(fill="both", expand=True)
        frame, tree = tema.criar_tree(moldura, [
            ("t", "Tecnologia", 150, "w"), ("n", "Senioridade", 100, "w"), ("mn", "Mín. médio", 120, "e"),
            ("md", "Médio", 120, "e"), ("mx", "Máx. médio", 120, "e"), ("q", "Vagas", 60, "e")], altura=4)
        frame.pack(fill="both", expand=True)
        for s in dados["estatistica_salarial_relacionada"]:
            tema.inserir(tree, (
                s["tecnologia"], fmt.formatar_senioridade(s["senioridade"]),
                fmt.formatar_moeda(s["salario_min_medio"]), fmt.formatar_moeda(s["salario_medio"]),
                fmt.formatar_moeda(s["salario_max_medio"]), s["total_vagas"]))
        if not dados["estatistica_salarial_relacionada"]:
            tema.inserir(tree, ("Sem dados salariais suficientes", "", "", "", "", ""))

        bt = ttk.Frame(corpo)
        bt.pack(fill="x", pady=(16, 0))
        if v["url_original"]:
            ttk.Button(bt, text="Abrir vaga original", command=lambda: webbrowser.open(v["url_original"])).pack(side="left")
        ttk.Button(bt, text="Fechar", style="Primario.TButton", command=self.destroy).pack(side="right")
        self.bind("<Escape>", lambda _e: self.destroy())
        tema.centralizar(self, pai, 780, 700)


class ComparacaoVagas(tk.Toplevel):
    def __init__(self, pai, vagas):
        super().__init__(pai)
        self.title("Comparação de vagas")
        self.configure(bg=tema.FUNDO)
        corpo = ttk.Frame(self, padding=24)
        corpo.pack(fill="both", expand=True)
        ttk.Label(corpo, text="Comparar vagas", style="Titulo.TLabel").pack(anchor="w", pady=(0, 12))
        colunas = [("attr", "Atributo", 130, "w")] + [(f"v{v['id']}", f"#{v['id']}", 210, "w") for v in vagas]
        moldura = ttk.Frame(corpo, style="Card.TFrame", padding=1)
        moldura.pack(fill="both", expand=True)
        frame, tree = tema.criar_tree(moldura, colunas, altura=9, selectmode="browse")
        frame.pack(fill="both", expand=True)
        linhas = [
            ("Título", lambda v: v["titulo"]), ("Empresa", lambda v: v["empresa"]),
            ("Local", lambda v: v["localizacao"] or ", ".join(x for x in (v["cidade"], v["estado"]) if x) or "—"),
            ("Modalidade", lambda v: fmt.formatar_modalidade(v["modalidade"])),
            ("Senioridade", lambda v: fmt.formatar_senioridade(v["senioridade"])),
            ("Salário mínimo", lambda v: fmt.formatar_moeda(v["salario_min"], v["moeda"])),
            ("Salário máximo", lambda v: fmt.formatar_moeda(v["salario_max"], v["moeda"])),
            ("Tecnologias", lambda v: ", ".join(v["skills"]) or "—"),
            ("Publicação", lambda v: fmt.formatar_data(v["data_publicacao"]) or "—"),
        ]
        for rotulo, fn in linhas:
            tema.inserir(tree, [rotulo] + [fn(v) for v in vagas])
        ttk.Button(corpo, text="Fechar", style="Primario.TButton", command=self.destroy).pack(anchor="e", pady=(16, 0))
        self.bind("<Escape>", lambda _e: self.destroy())
        tema.centralizar(self, pai, min(1200, 230 + 215 * len(vagas)), 450)
