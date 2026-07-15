import http from "http";
import { google } from "googleapis";
import readline from "readline";

const CLIENT_ID = process.env.GOOGLE_CLIENT_ID;
const CLIENT_SECRET = process.env.GOOGLE_CLIENT_SECRET;
const REDIRECT_URI = "http://localhost:3001/oauth2callback";

if (!CLIENT_ID || !CLIENT_SECRET) {
  console.error("Defina GOOGLE_CLIENT_ID e GOOGLE_CLIENT_SECRET antes de rodar este script.");
  process.exit(1);
}

const oauth2Client = new google.auth.OAuth2(CLIENT_ID, CLIENT_SECRET, REDIRECT_URI);
const scopes = ["https://www.googleapis.com/auth/calendar.readonly"];
const authUrl = oauth2Client.generateAuthUrl({ access_type: "offline", scope: scopes, prompt: "consent" });

console.log("Abra esta URL no navegador e autorize a conta iFood da Lilian:\n");
console.log(authUrl);
console.log("\nAguardando retorno em http://localhost:3001/oauth2callback ...");

const server = http.createServer(async (req, res) => {
  try {
    const url = new URL(req.url, REDIRECT_URI);
    const code = url.searchParams.get("code");
    if (!code) {
      res.end("Código ausente.");
      return;
    }
    const { tokens } = await oauth2Client.getToken(code);
    res.end("OK. Pode voltar ao terminal.");
    console.log("\nGOOGLE_REFRESH_TOKEN=\"" + tokens.refresh_token + "\"\n");
    server.close();
  } catch (e) {
    console.error(e);
    res.end("Erro ao gerar token.");
    server.close();
  }
});
server.listen(3001);
