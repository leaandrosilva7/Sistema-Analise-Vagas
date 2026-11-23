import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import db, exemplos
from core.servicos import ErroValidacao, Servico, exportar_csv
from core.salary_stats import calcular_estatisticas_salariais, detectar_tecnologias
from core import formatadores as f
from core import supabase_sync


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.conn = db.conectar(os.path.join(self.tmp.name, "t.db"))
        self.s = Servico(self.conn)

    def tearDown(self):
        self.conn.close()
        self.tmp.cleanup()

    def nova(self, **kw):
        d = {"titulo": "Dev Python", "empresa": "ACME", "senioridade": "pleno",
             "modalidade": "remoto", "salario_min": "5000", "salario_max": "8000",
             "data_publicacao": f.hoje(), "estado": "SP", "cidade": "São Paulo"}
        d.update(kw)
        return self.s.criar_vaga(d, kw.get("skills", "Python, SQL"))


class TestAuth(Base):
    def test_registro_login(self):
        self.s.registrar("A@x.com", "123456", "Ana")
        self.assertEqual(self.s.login("a@x.com", "123456")["nome"], "Ana")
        with self.assertRaises(ErroValidacao):
            self.s.login("a@x.com", "errada")
        with self.assertRaises(ErroValidacao):
            self.s.registrar("a@x.com", "123456")
        with self.assertRaises(ErroValidacao):
            self.s.registrar("b@x.com", "123")
        with self.assertRaises(ErroValidacao):
            self.s.registrar("invalido", "123456")

    def test_senha_nao_em_texto_puro(self):
        self.s.registrar("a@x.com", "segredo123")
        row = self.conn.execute("SELECT senha_hash FROM usuario").fetchone()
        self.assertNotIn("segredo123", row[0])


class TestCrud(Base):
    def test_ciclo_completo(self):
        vid = self.nova()
        v = self.s.obter_vaga(vid)
        self.assertEqual(v["skills"], ["Python", "SQL"])
        self.s.atualizar_vaga(vid, {**v, "titulo": "Dev Sênior", "senioridade": "Sênior",
                                    "salario_min": 9000, "salario_max": 12000}, "Python, Docker")
        v = self.s.obter_vaga(vid)
        self.assertEqual((v["titulo"], v["senioridade"]), ("Dev Sênior", "senior"))
        self.assertEqual(v["skills"], ["Docker", "Python"])
        self.s.excluir_vaga(vid)
        with self.assertRaises(ErroValidacao):
            self.s.obter_vaga(vid)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM vaga_skill").fetchone()[0], 0)

    def test_validacoes(self):
        with self.assertRaises(ErroValidacao):
            self.nova(titulo="")
        with self.assertRaises(ErroValidacao):
            self.nova(salario_min="9000", salario_max="1000")
        with self.assertRaises(ErroValidacao):
            self.nova(salario_min="-5")
        with self.assertRaises(ErroValidacao):
            self.nova(data_publicacao="31/02/2026")
        with self.assertRaises(ErroValidacao):
            self.nova(url_original="ftp://x")

    def test_url_duplicada(self):
        self.nova(url_original="https://a.com/1")
        with self.assertRaises(ErroValidacao):
            self.nova(url_original="https://a.com/1")

    def test_skills_detectadas_automaticamente(self):
        vid = self.s.criar_vaga({"titulo": "Dev React e Node.js", "empresa": "X"})
        self.assertEqual(set(self.s.obter_vaga(vid)["skills"]), {"Node.js", "React"})

    def test_filtros(self):
        self.nova(titulo="A", senioridade="junior", modalidade="presencial", cidade="Recife", estado="PE", skills="Java")
        self.nova(titulo="B", senioridade="senior", modalidade="remoto", skills="Python")
        self.nova(titulo="C", data_publicacao="2020-01-01", skills="Python")
        L = lambda **k: self.s.listar_vagas(k)[1]  # noqa: E731
        self.assertEqual(L(), 3)
        self.assertEqual(L(tecnologia="pyth"), 2)
        self.assertEqual(L(cidade="recife"), 1)
        self.assertEqual(L(cidade="PE"), 1)
        self.assertEqual(L(senioridade="Júnior"), 1)
        self.assertEqual(L(modalidade="Remoto"), 2)
        self.assertEqual(L(periodo=30), 2)
        self.assertEqual(L(texto="B"), 1)

    def test_paginacao(self):
        for i in range(7):
            self.nova(titulo=f"V{i}", skills="Java")
        v1, total = self.s.listar_vagas({}, pagina=1, limite=3)
        v3, _ = self.s.listar_vagas({}, pagina=3, limite=3)
        self.assertEqual((len(v1), total, len(v3)), (3, 7, 1))

    def test_comparar(self):
        a, b = self.nova(titulo="A"), self.nova(titulo="B")
        self.assertEqual([v["titulo"] for v in self.s.comparar_vagas([b, a])], ["B", "A"])
        with self.assertRaises(ErroValidacao):
            self.s.comparar_vagas([a])


class TestStats(Base):
    def test_estatistica(self):
        v = [
            {"senioridade": "pleno", "moeda": "BRL", "salario_min": 4000, "salario_max": 6000, "skills": ["Python"]},
            {"senioridade": "pleno", "moeda": "BRL", "salario_min": 6000, "salario_max": 8000, "skills": ["Python"]},
            {"senioridade": "pleno", "moeda": "USD", "salario_min": 6000, "salario_max": 8000, "skills": ["Python"]},
            {"senioridade": "pleno", "moeda": "BRL", "salario_min": 9, "salario_max": 10, "skills": ["Python"]},
            {"senioridade": "pleno", "moeda": "BRL", "salario_min": 9000, "salario_max": 1000, "skills": ["Python"]},
        ]
        r = calcular_estatisticas_salariais(v)
        self.assertEqual(len(r), 1)
        self.assertEqual((r[0]["salario_medio"], r[0]["total_vagas"]), (6000.0, 2))
        self.assertEqual(calcular_estatisticas_salariais(v, tecnologia="java"), [])

    def test_detectar(self):
        self.assertEqual(set(detectar_tecnologias("Vaga C# e .NET, Python/SQL")), {"C#", ".NET", "Python", "SQL"})
        self.assertNotIn("Java", detectar_tecnologias("JavaScript"))

    def test_dashboard(self):
        self.s.importar_vagas(exemplos.gerar(40))
        m = self.s.metricas()
        self.assertEqual(m["total_vagas"], 40)
        self.assertGreater(m["salario_medio"], 1000)
        self.assertNotEqual(m["skill_top"], "N/A")
        self.assertEqual(sum(t["total_vagas"] for t in self.s.tendencias()), 40)
        self.assertTrue(self.s.tecnologias_demandadas())
        self.assertIn("Total de vagas", self.s.relatorio_texto())

    def test_dashboard_vazio(self):
        m = self.s.metricas()
        self.assertEqual((m["total_vagas"], m["skill_top"]), (0, "N/A"))
        self.assertIn("sem dados", self.s.relatorio_texto())


class TestImport(Base):
    def test_dedupe_e_rejeitadas(self):
        r = self.s.importar_vagas([
            {"titulo": "A", "empresa": "X", "url_original": "https://a/1"},
            {"titulo": "A", "empresa": "X", "url_original": "https://a/1"},
            {"titulo": "B", "empresa": "X", "fonte": "f", "id_externo": "9"},
            {"titulo": "", "empresa": "X", "url_original": "https://a/3"},
            {"titulo": "D", "empresa": "X"},
        ])
        self.assertEqual((r["inseridas"], r["duplicadas"], r["rejeitadas"]), (2, 1, 2))
        r2 = self.s.importar_vagas(exemplos.gerar(5))
        r3 = self.s.importar_vagas(exemplos.gerar(5))
        self.assertEqual((r2["inseridas"], r3["inseridas"], r3["duplicadas"]), (5, 0, 5))

    def test_arquivos(self):
        csvp = os.path.join(self.tmp.name, "v.csv")
        with open(csvp, "w", encoding="utf-8") as fh:
            fh.write("titulo;empresa;url_original;salario_min;skills\nDev;ACME;https://x/1;5.000,50;Python,SQL\n")
        r = self.s.importar_arquivo(csvp)
        self.assertEqual(r["inseridas"], 1)
        v = self.s.listar_vagas()[0][0]
        self.assertEqual((v["salario_min"], v["skills"]), (5000.5, ["Python", "SQL"]))
        jp = os.path.join(self.tmp.name, "v.json")
        with open(jp, "w", encoding="utf-8") as fh:
            fh.write('{"vagas":[{"titulo":"J","empresa":"E","url_original":"https://x/2"}]}')
        self.assertEqual(self.s.importar_arquivo(jp)["inseridas"], 1)

    def test_csv_export_protege_formula(self):
        p = os.path.join(self.tmp.name, "o.csv")
        exportar_csv(p, ["a"], [["=1+1"], ["ok"]])
        with open(p, encoding="utf-8-sig") as fh:
            txt = fh.read()
        self.assertIn("'=1+1", txt)


class TestSync(Base):
    def remoto(self, **kw):
        from datetime import date
        r = {"id": 1, "fonte": "adzuna", "id_externo": "A1", "titulo": "Dev Python", "empresa": "X", "cidade": "SP",
             "estado": "SP", "localizacao": "São Paulo", "modalidade": "Remoto", "senioridade": "Sênior",
             "salario_min": 5000, "salario_max": 9000, "descricao": "usa Python", "url_original": "https://a/1",
             "data_publicacao": date(2026, 11, 20), "data_coleta": date(2026, 11, 21), "pais": "BR  ",
             "moeda": "BRL ", "salario_estimado": False, "url_normalizada": None}
        r.update(kw)
        return r

    def test_insere_atualiza_e_preserva_locais(self):
        local = self.nova(titulo="Só local")
        r1 = supabase_sync.aplicar_remotos(self.conn, [self.remoto(), self.remoto(id=2, id_externo="A2", url_original="https://a/2", titulo="")],
                                           {1: ["Python", "SQL"]})
        self.assertEqual((r1["inseridas"], r1["ignoradas"]), (1, 1))
        v = [x for x in self.s.listar_vagas()[0] if x["fonte"] == "adzuna"][0]
        self.assertEqual((v["moeda"], v["senioridade"], v["data_publicacao"], v["skills"]), ("BRL", "senior", "2026-11-20", ["Python", "SQL"]))
        r2 = supabase_sync.aplicar_remotos(self.conn, [self.remoto(titulo="Dev Python Sr", salario_max=12000)], {1: ["Python"]})
        self.assertEqual((r2["inseridas"], r2["atualizadas"]), (0, 1))
        self.assertEqual(self.s.total_vagas(), 2)
        self.assertEqual(self.s.obter_vaga(local)["titulo"], "Só local")
        self.assertEqual(self.s.obter_vaga(v["id"])["skills"], ["Python"])

    def test_dados_sujos(self):
        r = supabase_sync.aplicar_remotos(self.conn, [self.remoto(salario_min=9000, salario_max=1000), self.remoto(id=3, id_externo="A3", url_original="https://a/3", salario_min=-5)], {})
        self.assertEqual(r["inseridas"], 2)

    def test_env(self):
        p = os.path.join(self.tmp.name, ".env")
        with open(p, "w") as fh:
            fh.write("# c\nDATABASE_URL=postgresql://u:p@h:6543/postgres\nX='a b'\n")
        self.assertEqual(supabase_sync.ler_env([p])["DATABASE_URL"], "postgresql://u:p@h:6543/postgres")
        with self.assertRaises(supabase_sync.ErroSync):
            supabase_sync.buscar_remoto("")


class TestFormatadores(unittest.TestCase):
    def test_formatos(self):
        self.assertEqual(f.formatar_moeda(1234.5), "R$ 1.234,50")
        self.assertEqual(f.formatar_moeda(None), "Não informado")
        self.assertEqual(f.parse_numero("5.000,50"), 5000.5)
        self.assertEqual(f.parse_data("23/11/2026"), "2026-11-23")
        self.assertEqual(f.normalizar_senioridade("SÊNIOR"), "senior")
        self.assertEqual(f.normalizar_modalidade("Home Office"), "remoto")
        with self.assertRaises(ValueError):
            f.parse_numero("abc")


if __name__ == "__main__":
    unittest.main()
