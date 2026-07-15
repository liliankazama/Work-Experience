"use client";

import { useEffect, useMemo, useState } from "react";
import "./styles.css";

function fmtDate(iso) {
  const d = new Date(iso + "T12:00:00");
  return new Intl.DateTimeFormat("pt-BR", { weekday: "long", day: "numeric", month: "short" }).format(d);
}

function monthLabel(iso) {
  const d = new Date(iso + "T12:00:00");
  return new Intl.DateTimeFormat("pt-BR", { month: "long", year: "numeric" }).format(d);
}

function Slot({ slot, kind }) {
  return <span className={`slot ${kind}`}><span className="dot" />{slot.start}–{slot.end}</span>;
}

export default function Page() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const token = useMemo(() => {
    if (typeof window === "undefined") return "";
    return new URLSearchParams(window.location.search).get("t") || "";
  }, []);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`/api/availability?t=${encodeURIComponent(token)}`, { cache: "no-store" });
      const json = await res.json();
      if (!res.ok) throw new Error(json.error || "Não foi possível carregar a agenda.");
      setData(json);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  const byMonth = useMemo(() => {
    if (!data) return [];
    const groups = new Map();
    for (const day of data.days) {
      const key = day.date.slice(0, 7);
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(day);
    }
    return [...groups.entries()];
  }, [data]);

  return (
    <>
      <header className="hero">
        <div className="wrap">
          <div className="eyebrow">Agenda iFood · síncrona · privacidade segura</div>
          <h1>Agenda da Lilian</h1>
          <p>Blocos livres e ocupados dos próximos 3 meses para facilitar agendamentos com o Matheus — sem títulos, convidados ou detalhes internos.</p>
          <div className="actions">
            <button className="btn" onClick={load}>{loading ? "Atualizando..." : "Atualizar agora"}</button>
            <a className="btn secondary" href="#meses">Ver por mês</a>
          </div>
        </div>
      </header>

      <main className="wrap">
        {error && <div className="note danger"><b>Erro:</b> {error}</div>}
        {!token && <div className="note danger"><b>Token ausente:</b> abra a URL com <code>?t=SEU_TOKEN</code>.</div>}
        {loading && !data && <div className="note">Carregando agenda ao vivo...</div>}

        {data && (
          <>
            <div className="grid">
              <div className="stat"><b>{data.rangeLabel}</b><span>janela da agenda</span></div>
              <div className="stat"><b>{data.stats.eventsRead}</b><span>eventos lidos da agenda iFood</span></div>
              <div className="stat"><b>{data.stats.busyHours}</b><span>ocupada em dias úteis, 08h–20h</span></div>
              <div className="stat"><b>{data.stats.freeHours}</b><span>livres em dias úteis até 18h</span></div>
            </div>

            <div className="note"><b>Atualizado agora:</b> {data.generatedAtLabel}. Esta página consulta a agenda iFood ao abrir ou ao tocar em “Atualizar agora”. Os detalhes das reuniões ficam no servidor e não são enviados ao navegador.</div>

            <h2 className="section-title">Melhores janelas livres próximas</h2>
            <div className="suggestions">
              {data.suggestions.map((s, i) => <div className="pill" key={i}>{s.start}–{s.end}<small>{fmtDate(s.date)} · {s.minutes} min livres</small></div>)}
              {data.suggestions.length === 0 && <div className="empty">Sem janelas úteis encontradas.</div>}
            </div>

            <h2 id="meses" className="section-title">Agenda por mês</h2>
            {byMonth.map(([month, days], idx) => (
              <details className="month" key={month} open={idx === 0}>
                <summary><span>{monthLabel(days[0].date)}</span><span className="month-meta">{days.length} dias</span></summary>
                <div className="days">
                  {days.map(day => (
                    <section className="day" key={day.date}>
                      <div className="day-head">
                        <h3>{fmtDate(day.date)}</h3>
                        <span className={day.free.length ? "badge free" : "badge"}>{day.weekend ? "Fim de semana" : day.free.length ? `${day.free.length} janela(s) livre(s)` : "Sem janela livre"}</span>
                      </div>
                      {day.notes.length > 0 && <div className="note compact">Dia todo: {day.notes.join("; ")}</div>}
                      <div className="slots">
                        <div className="col"><h4>Livre</h4>{day.free.length ? day.free.map((s, i) => <Slot key={i} slot={s} kind="free" />) : <div className="empty">Nenhum bloco.</div>}</div>
                        <div className="col"><h4>Ocupada</h4>{day.busy.length ? day.busy.map((s, i) => <Slot key={i} slot={s} kind="busy" />) : <div className="empty">Nenhum bloco.</div>}</div>
                      </div>
                    </section>
                  ))}
                </div>
              </details>
            ))}
          </>
        )}
      </main>
    </>
  );
}
