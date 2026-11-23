"""Teste de fumaça da interface (precisa de display; use xvfb-run em servidores)."""
import os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tkinter import messagebox
messagebox.showinfo = lambda *a, **k: None
messagebox.askyesno = lambda *a, **k: True
messagebox.showwarning = lambda *a, **k: None
from ui.principal import Aplicacao
from ui.vagas import FormularioVaga, DetalhesVaga, ComparacaoVagas
from core import exemplos

saida = sys.argv[1] if len(sys.argv) > 1 else None
tmp = tempfile.mkdtemp()
app = Aplicacao(os.path.join(tmp, "t.db"))
app.update()
def shot(nome):
    app.update_idletasks(); app.update()
    if saida:
        os.system(f"import -window root {saida}/{nome}.png 2>/dev/null")

shot("1_login")
# registro + login
t = app.conteudo
t.alternar(); app.update()
t.var_nome.set("Ana"); t.var_email.set("ana@x.com"); t.var_senha.set("123456"); t.var_conf.set("123456")
t.enviar(); app.update()
assert app.usuario and app.usuario["email"] == "ana@x.com"
app.servico.importar_vagas(exemplos.gerar(80)); app.atualizar_tudo(); app.vagas.carregar()
app.update()
assert app.dash.cv_techs.dados, "gráfico sem dados"
shot("2_dashboard")
app.abas.select(app.vagas); app.update(); shot("3_vagas")
assert len(app.vagas.tree.get_children()) == 30
app.vagas.ir_pagina(2); assert len(app.vagas.tree.get_children()) == 30
app.vagas.ir_pagina(3); assert len(app.vagas.tree.get_children()) == 20
app.vagas.cb_sen.set("Sênior"); app.vagas.buscar(); n_sen = app.vagas.total
assert 0 < n_sen < 80
app.vagas.limpar(); assert app.vagas.total == 80
# CRUD via formulário
f = FormularioVaga(app.vagas, app.servico, None, app.vagas._salvou); app.update()
f.vars["titulo"].set("Dev Rust Teste"); f.vars["empresa"].set("Acme"); f.vars["salario_min"].set("7.000,00")
f.vars["salario_max"].set("9000"); f.vars["skills"].set("Rust, Linux"); f.cb_sen.set("Pleno")
shot("4_form"); f.salvar(); app.update()
assert app.servico.total_vagas() == 81
vid = app.servico.listar_vagas({"texto": "Rust Teste"})[0][0]["id"]
f = FormularioVaga(app.vagas, app.servico, vid, app.vagas._salvou); app.update()
assert f.vars["salario_min"].get() == "7000", f.vars["salario_min"].get()
f.vars["titulo"].set("Dev Rust Alterado"); f.salvar(); app.update()
assert app.servico.obter_vaga(vid)["titulo"] == "Dev Rust Alterado"
# erro de validação mostrado no form, sem fechar
f = FormularioVaga(app.vagas, app.servico, None, lambda: None); app.update()
f.vars["titulo"].set("x"); f.vars["empresa"].set("y"); f.vars["data_publicacao"].set("99/99/9999"); f.salvar(); app.update()
assert f.winfo_exists() and "inválida" in f.lbl_erro.cget("text"); f.destroy()
# detalhes e comparação
d = DetalhesVaga(app.vagas, app.servico, vid); app.update(); shot("5_detalhes"); d.destroy()
ids = [v["id"] for v in app.servico.listar_vagas({}, 1, 3)[0]]
for i in ids: app.vagas.tree.selection_add(str(i))
c = ComparacaoVagas(app.vagas, app.servico.comparar_vagas(ids)); app.update(); shot("6_comparar"); c.destroy()
# exclusão
app.vagas.tree.selection_set(str(vid)); app.vagas.excluir(); app.update()
assert app.servico.total_vagas() == 80
app.abas.select(app.rel); app.update(); shot("7_relatorio")
assert "Total de vagas" in app.rel.txt.get("1.0", "end")
# logout / novo login
app.mostrar_login(); app.update(); assert app.usuario is None
t = app.conteudo; t.var_email.set("ana@x.com"); t.var_senha.set("errada"); t.enviar(); app.update()
assert "inválidos" in t.lbl_erro.cget("text")
app.sair()
print("SMOKE OK")
