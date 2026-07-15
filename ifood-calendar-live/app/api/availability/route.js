import { google } from "googleapis";

const TZ = process.env.APP_TIMEZONE || "America/Sao_Paulo";
const CALENDAR_ID = process.env.CALENDAR_ID || "lilian.kazama@ifood.com.br";
const MONTHS = Number(process.env.MONTHS || 3);
const WORK_START = 8;
const WORK_END = 20;
const FREE_MINUTES = 30;

export const dynamic = "force-dynamic";

function pad(n) { return String(n).padStart(2, "0"); }
function dateKey(d) { return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}`; }
function addDays(d, n) { const x = new Date(d); x.setDate(x.getDate()+n); return x; }
function addMonths(d, n) { const x = new Date(d); x.setMonth(x.getMonth()+n); return x; }
function minutesOfDay(d) { return d.getHours()*60 + d.getMinutes(); }
function toTime(m) { return `${pad(Math.floor(m/60))}:${pad(m%60)}`; }
function fmtHours(minutes) { return `${Math.floor(minutes/60)}h${pad(minutes%60)}`; }
function clamp(v, min, max) { return Math.max(min, Math.min(max, v)); }
function isWeekend(key) { const d = new Date(key + "T12:00:00"); return d.getDay() === 0 || d.getDay() === 6; }
function localDateFromISO(iso) { return new Date(iso); }

function allDateKeys(start, end) {
  const out = [];
  for (let d = new Date(start); d <= end; d = addDays(d, 1)) out.push(dateKey(d));
  return out;
}

function mergeIntervals(intervals) {
  const sorted = intervals.filter(x => x.end > x.start).sort((a,b) => a.start - b.start);
  const out = [];
  for (const cur of sorted) {
    const last = out[out.length-1];
    if (!last || cur.start > last.end) out.push({...cur});
    else last.end = Math.max(last.end, cur.end);
  }
  return out;
}

async function getEvents(timeMin, timeMax) {
  const oauth2Client = new google.auth.OAuth2(
    process.env.GOOGLE_CLIENT_ID,
    process.env.GOOGLE_CLIENT_SECRET
  );
  oauth2Client.setCredentials({ refresh_token: process.env.GOOGLE_REFRESH_TOKEN });
  const calendar = google.calendar({ version: "v3", auth: oauth2Client });
  const events = [];
  let pageToken;
  do {
    const res = await calendar.events.list({
      calendarId: CALENDAR_ID,
      timeMin: timeMin.toISOString(),
      timeMax: timeMax.toISOString(),
      singleEvents: true,
      orderBy: "startTime",
      maxResults: 2500,
      pageToken
    });
    events.push(...(res.data.items || []));
    pageToken = res.data.nextPageToken;
  } while (pageToken);
  return events;
}

export async function GET(req) {
  try {
    const url = new URL(req.url);
    const token = url.searchParams.get("t") || req.headers.get("x-shared-token") || "";
    if (!process.env.SHARED_PAGE_TOKEN || token !== process.env.SHARED_PAGE_TOKEN) {
      return Response.json({ error: "Acesso não autorizado." }, { status: 401 });
    }
    for (const name of ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_REFRESH_TOKEN"]) {
      if (!process.env[name]) return Response.json({ error: `Variável ausente: ${name}` }, { status: 500 });
    }

    const now = new Date();
    const start = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const end = addMonths(start, MONTHS);
    const events = await getEvents(start, addDays(end, 1));

    const busyByDay = new Map();
    const notesByDay = new Map();
    for (const key of allDateKeys(start, end)) {
      busyByDay.set(key, []);
      notesByDay.set(key, []);
    }

    for (const ev of events) {
      const summary = ev.summary || "";
      const stRaw = ev.start?.dateTime || ev.start?.date;
      const enRaw = ev.end?.dateTime || ev.end?.date;
      if (!stRaw || !enRaw) continue;

      const isAllDay = !!ev.start?.date;
      if (isAllDay) {
        const sd = new Date(stRaw + "T00:00:00");
        const edExclusive = new Date(enRaw + "T00:00:00");
        for (let d = sd; d < edExclusive; d = addDays(d, 1)) {
          const key = dateKey(d);
          if (!busyByDay.has(key)) continue;
          if (/Férias Lilian/i.test(summary)) {
            notesByDay.get(key).push("Férias Lilian");
            busyByDay.get(key).push({ start: WORK_START*60, end: WORK_END*60 });
          } else if (/^\s*SP\s*$/i.test(summary)) {
            notesByDay.get(key).push("SP");
          }
        }
        continue;
      }

      const st = localDateFromISO(stRaw);
      const en = localDateFromISO(enRaw);
      if (en <= now) continue;
      const hours = (en - st) / 36e5;
      if (hours >= 12 && /Lembrete: Férias (?!Lilian)/i.test(summary)) continue;
      if (hours >= 12 && /Férias Lilian/i.test(summary)) {
        for (let d = new Date(st.getFullYear(), st.getMonth(), st.getDate()); d <= en; d = addDays(d, 1)) {
          const key = dateKey(d);
          if (!busyByDay.has(key)) continue;
          notesByDay.get(key).push("Férias Lilian");
          busyByDay.get(key).push({ start: WORK_START*60, end: WORK_END*60 });
        }
        continue;
      }

      for (let d = new Date(st.getFullYear(), st.getMonth(), st.getDate()); d <= en; d = addDays(d, 1)) {
        const key = dateKey(d);
        if (!busyByDay.has(key)) continue;
        let a = dateKey(st) === key ? minutesOfDay(st) : 0;
        let b = dateKey(en) === key ? minutesOfDay(en) : 24*60;
        if (dateKey(now) === key) a = Math.max(a, minutesOfDay(now));
        a = clamp(a, WORK_START*60, WORK_END*60);
        b = clamp(b, WORK_START*60, WORK_END*60);
        if (b > a) busyByDay.get(key).push({ start: a, end: b });
      }
    }

    const days = [];
    let busyMinutes = 0;
    let freeMinutes = 0;
    const suggestions = [];

    for (const key of allDateKeys(start, end)) {
      const weekend = isWeekend(key);
      let dayStart = WORK_START*60;
      const dayEnd = WORK_END*60;
      if (key === dateKey(now)) {
        const m = minutesOfDay(now);
        dayStart = Math.max(dayStart, m <= 30 ? Math.floor(m/60)*60 + 30 : (Math.floor(m/60)+1)*60);
      }
      const busy = mergeIntervals(busyByDay.get(key).map(x => ({ start: clamp(x.start, dayStart, dayEnd), end: clamp(x.end, dayStart, dayEnd) })));
      const free = [];
      let pointer = dayStart;
      for (const b of busy) {
        if (b.start > pointer && b.start - pointer >= FREE_MINUTES) free.push({ start: pointer, end: b.start });
        pointer = Math.max(pointer, b.end);
      }
      if (dayEnd > pointer && dayEnd - pointer >= FREE_MINUTES) free.push({ start: pointer, end: dayEnd });

      if (!weekend) {
        busyMinutes += busy.reduce((sum, x) => sum + (x.end-x.start), 0);
        for (const f of free) {
          const until18 = Math.min(f.end, 18*60);
          if (until18 > f.start) freeMinutes += until18 - f.start;
          if (until18 > f.start && until18 - f.start >= 45 && suggestions.length < 20) {
            suggestions.push({ date: key, start: toTime(f.start), end: toTime(until18), minutes: until18 - f.start });
          }
        }
      }

      days.push({
        date: key,
        weekend,
        notes: [...new Set(notesByDay.get(key))],
        busy: busy.map(x => ({ start: toTime(x.start), end: toTime(x.end) })),
        free: free.map(x => ({ start: toTime(x.start), end: toTime(x.end) }))
      });
    }

    const generatedAtLabel = new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "short", timeZone: TZ }).format(new Date());
    return Response.json({
      generatedAt: new Date().toISOString(),
      generatedAtLabel,
      rangeLabel: `${MONTHS} meses`,
      stats: { eventsRead: events.length, busyHours: fmtHours(busyMinutes), freeHours: fmtHours(freeMinutes) },
      suggestions,
      days
    }, { headers: { "Cache-Control": "no-store, max-age=0" } });
  } catch (e) {
    console.error(e);
    return Response.json({ error: "Falha ao consultar a agenda." }, { status: 500 });
  }
}
