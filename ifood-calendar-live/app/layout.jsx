export const metadata = {
  title: "Agenda da Lilian · iFood",
  description: "Blocos livres e ocupados, sem detalhes de reuniões."
};

export default function RootLayout({ children }) {
  return (
    <html lang="pt-BR">
      <body>{children}</body>
    </html>
  );
}
