# Agenda iFood live — Lilian

Página síncrona para compartilhar com o Matheus: mostra **apenas blocos livres/ocupados** da agenda iFood, sem títulos de reuniões, convidados ou detalhes internos.

## O que ela faz

- Consulta a agenda `lilian.kazama@ifood.com.br` em tempo real.
- Mostra os próximos **3 meses**.
- Agrupa por mês.
- Oculta detalhes dos eventos no backend.
- Usa um token simples na URL para evitar acesso acidental.

## Deploy recomendado

Use Vercel, Render, Railway ou outro host que rode Next.js com API routes.

## Variáveis de ambiente

Copie `.env.example` para `.env.local` no desenvolvimento e configure no host:

```env
GOOGLE_CLIENT_ID="..."
GOOGLE_CLIENT_SECRET="..."
GOOGLE_REFRESH_TOKEN="..."
CALENDAR_ID="lilian.kazama@ifood.com.br"
APP_TIMEZONE="America/Sao_Paulo"
SHARED_PAGE_TOKEN="um-token-longo"
MONTHS="3"
```

## Como gerar o GOOGLE_REFRESH_TOKEN

1. Crie um projeto no Google Cloud Console.
2. Ative **Google Calendar API**.
3. Crie um OAuth Client do tipo **Web application**.
4. Adicione o redirect URI: `http://localhost:3001/oauth2callback`.
5. Rode localmente:

```bash
npm install
GOOGLE_CLIENT_ID="..." GOOGLE_CLIENT_SECRET="..." npm run get-refresh-token
```

6. Abra a URL impressa, autorize a conta iFood da Lilian e copie o `GOOGLE_REFRESH_TOKEN`.
7. Configure esse token no host.

## URL para compartilhar

Depois do deploy, abra:

```text
https://SEU-DOMINIO.com?t=SHARED_PAGE_TOKEN
```

Esse é o link para enviar ao Matheus.

## Segurança e privacidade

- O frontend nunca recebe títulos de reuniões, convidados, descrições ou locais.
- O backend retorna só intervalos `Livre` e `Ocupada`.
- O token na URL é uma proteção simples; não é login forte.
- Para segurança maior, use autenticação do próprio host ou Cloudflare Access.

## Ajustes rápidos

- Mudar janela: `MONTHS="6"`.
- Mudar agenda: `CALENDAR_ID="outro@email.com"`.
- Mudar horário analisado: edite `WORK_START` e `WORK_END` em `app/api/availability/route.js`.
