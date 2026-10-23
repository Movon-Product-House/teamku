import { notFound } from "next/navigation";
import { DesignSystemPage } from "@/features/design-system/components/design-system-page";

// Referensi visual token & komponen v2. Hanya di dev server (`next dev`), tidak di build produksi.
export default function Page() {
  if (process.env.NODE_ENV === "production") notFound();
  return <DesignSystemPage />;
}
