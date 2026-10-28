import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Skripsi Formatter — Periksa & Rapikan Format Word Otomatis",
  description:
    "Tool web untuk memeriksa dan merapikan format skripsi, tugas akhir, atau laporan mahasiswa (.docx) sesuai pedoman kampus tanpa mengubah isi tulisan.",
  keywords: ["skripsi", "tugas akhir", "word formatter", "docx", "format skripsi otomatis"],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="id">
      <body>{children}</body>
    </html>
  );
}
