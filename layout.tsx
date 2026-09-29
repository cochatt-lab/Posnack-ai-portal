export const metadata = { title: "Posnack School AI Learning Portal" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body style={{ margin: 0, fontFamily: "Arial, sans-serif", background: "#f6f8fa" }}>
        {children}
      </body>
    </html>
  );
}
