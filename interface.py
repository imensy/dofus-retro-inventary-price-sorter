#!/usr/bin/env python3
"""
interface.py - interface (no navegador) para o leitor de itens do Dofus Retro.

  cd ~/Desktop/dofus_reader
  sudo python3 interface.py
  -> abra http://127.0.0.1:8765  (so voce acessa, o servidor escuta apenas em localhost)

O botao "Atualizar" le a RAM do jogo (read-only) e monta a lista por categoria.
Ordenar/filtrar acontece so aqui na pagina; nada e enviado ao jogo.
"""
import argparse, json, os, subprocess, sys, threading, time, webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import script as core  # noqa: E402

STATE = {"running": False, "pct": 0, "msg": "", "result": None, "error": None, "saved": None}
LOCK = threading.Lock()
ARGS = None


def do_scan():
    def prog(p, m):
        STATE["pct"], STATE["msg"] = p, m
    try:
        res = core.run_scan(ARGS.proc, ARGS.pid, prog)
        STATE["saved"] = core.save_outputs(res, os.path.join(HERE, "outputs"))
        STATE["result"], STATE["error"] = res, None
    except PermissionError:
        STATE["error"] = "Sem permissao para ler a memoria. Rode com: sudo python3 interface.py"
    except Exception as e:  # noqa: BLE001
        STATE["error"] = str(e)
    finally:
        STATE["running"] = False


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _ok_host(self):
        return self.headers.get("Host", "").split(":")[0] in ("127.0.0.1", "localhost")

    def _send(self, code, body, ctype="application/json"):
        b = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        if not self._ok_host():
            return self._send(403, "{}")
        if self.path in ("/", "/index.html"):
            return self._send(200, PAGE, "text/html")
        if self.path == "/api/state":
            return self._send(200, json.dumps(STATE, ensure_ascii=False))
        self._send(404, "{}")

    def do_POST(self):
        if not self._ok_host() or self.path != "/api/scan":
            return self._send(403, "{}")
        with LOCK:
            if not STATE["running"]:
                STATE.update(running=True, pct=0, msg="Iniciando...", error=None)
                threading.Thread(target=do_scan, daemon=True).start()
        self._send(200, json.dumps({"ok": True}))


PAGE = r"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Itens Dofus Retro</title>
<style>
:root{--bg:#f6f3ea;--panel:#fffdf7;--ink:#2b2418;--mute:#7a6f5a;--line:#e3dcc8;--accent:#c2561b;--accent-ink:#fff;--chip:#efe9d8;--ok:#2f7d4f}
@media (prefers-color-scheme:dark){:root{--bg:#1d1a14;--panel:#26221a;--ink:#efe8d6;--mute:#a79c84;--line:#3a3427;--accent:#e0743a;--accent-ink:#1d1a14;--chip:#332e22;--ok:#6fc08f}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.45 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
.wrap{max-width:980px;margin:0 auto;padding:20px 16px 60px}
header{display:flex;flex-wrap:wrap;align-items:center;gap:14px;margin-bottom:16px}
h1{font-size:20px;margin:0;font-weight:650;letter-spacing:.2px}
.sp{flex:1}
button{font:inherit;cursor:pointer}
.btn{background:var(--accent);color:var(--accent-ink);border:0;border-radius:8px;padding:9px 18px;font-weight:600}
.btn:disabled{opacity:.55;cursor:wait}
.btn.ghost{background:transparent;color:var(--ink);border:1px solid var(--line);font-weight:500;padding:7px 12px}
.bar{height:4px;background:var(--line);border-radius:4px;overflow:hidden;margin:0 0 6px;display:none}
.bar>i{display:block;height:100%;width:0;background:var(--accent);transition:width .25s}
.status{color:var(--mute);font-size:13px;min-height:19px;margin-bottom:12px}
.status.err{color:#c0392b}
.controls{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin-bottom:12px}
.seg{display:inline-flex;border:1px solid var(--line);border-radius:8px;overflow:hidden}
.seg button{background:var(--panel);color:var(--ink);border:0;padding:7px 12px;border-right:1px solid var(--line)}
.seg button:last-child{border-right:0}
.seg button.on{background:var(--ink);color:var(--bg)}
select,input[type=search]{font:inherit;background:var(--panel);color:var(--ink);border:1px solid var(--line);border-radius:8px;padding:7px 10px}
input[type=search]{min-width:170px}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin:4px 0 16px}
.chip{background:var(--chip);color:var(--ink);border:1px solid transparent;border-radius:999px;padding:5px 12px;font-size:13px}
.chip b{font-weight:650;margin-left:4px;color:var(--mute)}
.chip.on{border-color:var(--accent);background:var(--panel)}
details.cat{background:var(--panel);border:1px solid var(--line);border-radius:12px;margin-bottom:12px;overflow:hidden}
details.cat>summary{cursor:pointer;list-style:none;display:flex;align-items:center;gap:10px;padding:12px 16px;font-weight:650}
details.cat>summary::-webkit-details-marker{display:none}
details.cat>summary::before{content:"▸";color:var(--mute);transition:transform .15s}
details.cat[open]>summary::before{transform:rotate(90deg)}
.cnt{color:var(--mute);font-weight:400;font-size:13px}
table{width:100%;border-collapse:collapse;table-layout:fixed}
th.num{width:15%}th.tp{width:24%}td{overflow:hidden;text-overflow:ellipsis}
th,td{padding:7px 16px;text-align:left;border-top:1px solid var(--line)}
th{font-size:12px;text-transform:uppercase;letter-spacing:.5px;color:var(--mute);font-weight:600;cursor:pointer;user-select:none;white-space:nowrap}
th.num,td.num{text-align:right;font-variant-numeric:tabular-nums}
td.zero{color:var(--mute);opacity:.5}
td.tipo{color:var(--mute);font-size:13px}
.empty{padding:40px 10px;text-align:center;color:var(--mute)}
details.src{margin:0 0 14px;color:var(--mute);font-size:13px}
details.src summary{cursor:pointer}
details.src .row{display:flex;flex-wrap:wrap;gap:10px;margin-top:8px;align-items:center}
details.src select{max-width:100%}
@media(max-width:560px){th,td{padding:7px 10px}.hide-s{display:none}}
</style></head><body><div class="wrap">
<header><h1>Itens · Dofus Retro</h1><div class="sp"></div>
<button class="btn ghost" id="csv" disabled>Exportar CSV</button>
<button class="btn" id="go">Atualizar</button></header>
<div class="bar" id="bar"><i id="barfill"></i></div>
<div class="status" id="status">Clique em Atualizar com o jogo aberto (baú/banco aberto para ler o banco).</div>

<details class="src" id="src" style="display:none"><summary>Fonte dos dados (cópias na RAM)</summary>
<div class="row"><label>Inventário <select id="selInv"></select></label>
<label>Banco <select id="selBau"></select></label></div>
<div style="margin-top:6px">A RAM pode guardar cópias antigas. Se a lista não bate com o jogo, escolha outra cópia.</div></details>

<div class="controls" id="controls" style="display:none">
<div class="seg" id="loc"><button data-v="both" class="on">Ambos</button><button data-v="inv">Inventário</button><button data-v="bau">Banco</button></div>
<label>Ordenar
<select id="sort"><option value="n-asc">Nome A → Z</option><option value="n-desc">Nome Z → A</option>
<option value="q-desc">Quantidade maior → menor</option><option value="q-asc">Quantidade menor → maior</option></select></label>
<input type="search" id="q" placeholder="Buscar item…"></div>
<div class="chips" id="chips"></div>
<div id="list"></div></div>
<script>
const CATS=["Equipamento","Consumível","Recursos","Pedra de alma","Runa de forja mágica","Cartas","Itens de aparência","Desconhecido"];
const $=s=>document.querySelector(s);
const S={res:null,loc:"both",cat:"Todos",iInv:0,iBau:0,sort:"n-asc",q:"",open:{}};
const fmt=n=>n.toLocaleString("pt-BR");
function rows(){
  const R=S.res, M=R.meta, m=new Map();
  const add=(snap,key)=>{ if(!snap) return; for(const [t,q] of snap.items){ if(!m.has(t)) m.set(t,{id:t,inv:0,bau:0,...M[t]}); m.get(t)[key]+=q; } };
  if(S.loc!=="bau") add(R.snapshots.inv[S.iInv],"inv");
  if(S.loc!=="inv") add(R.snapshots.bau[S.iBau],"bau");
  return [...m.values()].map(r=>({...r,tot:r.inv+r.bau}));
}
function render(){
  if(!S.res) return;
  let all=rows();
  const q=S.q.trim().toLowerCase();
  if(q) all=all.filter(r=>r.n.toLowerCase().includes(q));
  const by={}; CATS.forEach(c=>by[c]=[]); all.forEach(r=>(by[r.c]||(by[r.c]=[])).push(r));
  const [k,dir]=S.sort.split("-"), sg=dir==="asc"?1:-1;
  const cmp=(a,b)=> k==="n" ? sg*a.n.localeCompare(b.n,"pt") : (sg*(a.tot-b.tot)||a.n.localeCompare(b.n,"pt"));
  Object.values(by).forEach(a=>a.sort(cmp));
  const cats=Object.keys(by).filter(c=>by[c].length);
  // chips
  $("#chips").innerHTML=[["Todos",all.length],...cats.map(c=>[c,by[c].length])].map(([c,n])=>
    `<button class="chip ${S.cat===c?"on":""}" data-c="${c}">${c}<b>${n}</b></button>`).join("");
  const show=S.cat==="Todos"?cats:cats.filter(c=>c===S.cat);
  if(!show.length){ $("#list").innerHTML='<div class="empty">Nenhum item para mostrar.</div>'; return; }
  const both=S.loc==="both";
  $("#list").innerHTML=show.map(c=>{
    const a=by[c], units=a.reduce((s,r)=>s+r.tot,0);
    const open=S.cat!=="Todos"||S.open[c]!==false;
    return `<details class="cat" data-c="${c}" ${open?"open":""}><summary>${c}<span class="cnt">${a.length} itens · ${fmt(units)} un.</span></summary>
    <table><thead><tr><th data-s="n">Nome</th><th class="hide-s tp">Tipo</th>
    ${both?'<th class="num" data-s="q">Inventário</th><th class="num" data-s="q">Banco</th>':""}
    <th class="num" data-s="q">${both?"Total":(S.loc==="inv"?"Inventário":"Banco")}</th></tr></thead><tbody>
    ${a.map(r=>`<tr><td>${esc(r.n)}</td><td class="tipo hide-s">${esc(r.tn||"")}</td>
    ${both?`<td class="num ${r.inv?"":"zero"}">${fmt(r.inv)}</td><td class="num ${r.bau?"":"zero"}">${fmt(r.bau)}</td>`:""}
    <td class="num">${fmt(r.tot)}</td></tr>`).join("")}</tbody></table></details>`}).join("");
}
const esc=s=>String(s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
function fillSel(sel,list,cur){
  sel.innerHTML=list.length?list.map((s,i)=>`<option value="${i}">Cópia ${i+1} · ${s.n} itens · ${fmt(s.units)} un. · ${s.copies}× na RAM</option>`).join(""):'<option>(nada encontrado)</option>';
  sel.value=cur;
}
function load(res){
  S.res=res; S.iInv=0; S.iBau=0;
  fillSel($("#selInv"),res.snapshots.inv,0); fillSel($("#selBau"),res.snapshots.bau,0);
  ["#src","#controls"].forEach(s=>$(s).style.display="");
  $("#csv").disabled=false; render();
}
$("#selInv").onchange=e=>{S.iInv=+e.target.value;render()};
$("#selBau").onchange=e=>{S.iBau=+e.target.value;render()};
$("#sort").onchange=e=>{S.sort=e.target.value;render()};
$("#q").oninput=e=>{S.q=e.target.value;render()};
$("#loc").onclick=e=>{const b=e.target.closest("button"); if(!b) return; S.loc=b.dataset.v;
  document.querySelectorAll("#loc button").forEach(x=>x.classList.toggle("on",x===b)); render()};
$("#chips").onclick=e=>{const b=e.target.closest(".chip"); if(!b) return; S.cat=b.dataset.c; render()};
$("#list").addEventListener("toggle",e=>{const d=e.target; if(d.dataset&&d.dataset.c&&S.cat==="Todos") S.open[d.dataset.c]=d.open},true);
$("#list").onclick=e=>{const th=e.target.closest("th[data-s]"); if(!th) return;
  const k=th.dataset.s, [ck,cd]=S.sort.split("-"); S.sort=k+"-"+(ck===k&&cd==="asc"?"desc":(ck===k?"asc":(k==="n"?"asc":"desc")));
  $("#sort").value=S.sort; render()};
$("#csv").onclick=()=>{ const r=rows(); const out=[["categoria","tipo","id","nome","inventario","banco","total"]];
  r.forEach(x=>out.push([x.c,x.tn||"",x.id,x.n,x.inv,x.bau,x.tot]));
  const txt="﻿"+out.map(l=>l.map(v=>'"'+String(v).replace(/"/g,'""')+'"').join(",")).join("\n");
  const a=document.createElement("a"); a.href=URL.createObjectURL(new Blob([txt],{type:"text/csv"}));
  a.download="itens.csv"; a.click(); };
let timer=null;
async function poll(){
  const st=await (await fetch("/api/state")).json();
  const bar=$("#bar"), fill=$("#barfill"), s=$("#status"), go=$("#go");
  if(st.running){ bar.style.display="block"; fill.style.width=st.pct+"%"; s.className="status"; s.textContent=`${st.msg} · ${st.pct}%`; go.disabled=true; return; }
  clearInterval(timer); timer=null; bar.style.display="none"; go.disabled=false;
  if(st.error){ s.className="status err"; s.textContent=st.error; return; }
  if(st.result){ load(st.result); const l=st.result.lang;
    s.className=l.base+l.disco+l.ram===0?"status err":"status"; s.textContent=(l.base+l.disco+l.ram===0?"ATENÇÃO: nenhuma base de nomes carregada. ":"")+`Leitura de ${st.result.when} · nomes: base ${l.base}, disco ${l.disco}, RAM ${l.ram}`+(st.saved?` · salvo em outputs/`:""); }
}
$("#go").onclick=async()=>{ $("#go").disabled=true; await fetch("/api/scan",{method:"POST"}); if(!timer) timer=setInterval(poll,400); poll(); };
poll().then(()=>{});
</script></body></html>"""


def main():
    global ARGS
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--proc", default="dofus1electron")
    ap.add_argument("--pid", type=int, action="append")
    ap.add_argument("--no-open", action="store_true")
    ARGS = ap.parse_args()
    srv = ThreadingHTTPServer(("127.0.0.1", ARGS.port), H)
    url = f"http://127.0.0.1:{ARGS.port}"
    print(f"Interface em {url}  (Ctrl+C para sair)")
    if not ARGS.no_open:
        try:
            if os.environ.get("SUDO_USER"):
                subprocess.Popen(["sudo", "-u", os.environ["SUDO_USER"], "xdg-open", url],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                webbrowser.open(url)
        except Exception:
            pass
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
