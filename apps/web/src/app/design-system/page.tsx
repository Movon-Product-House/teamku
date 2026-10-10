import { notFound } from "next/navigation";
import { DesignSystemPage } from "@/features/design-system/components/design-system-page";

// Referensi visual token & komponen v2. Tersedia di lokal dan preview Vercel, tidak di produksi.
export default function Page() {
  if (process.env.VERCEL_ENV === "production") notFound();
  return <DesignSystemPage />;
}
