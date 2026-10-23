import { Inbox, type LucideIcon, MapPinOff, ScanFace, UserX } from "lucide-react";
import Link from "next/link";
import { cn } from "@/shared/lib/cn";
import type { ActionItem } from "../manager-home";

const icons: Record<ActionItem["kind"], { icon: LucideIcon; tone: string }> = {
  leave: { icon: Inbox, tone: "text-brand" },
  outside_geofence: { icon: MapPinOff, tone: "text-warning" },
  missed_reverify: { icon: ScanFace, tone: "text-warning" },
  not_checked_in: { icon: UserX, tone: "text-faint-foreground" },
};

/** M1 "Perlu tindakan": every item links to where the manager acts on it. */
export function ManagerActions({ items }: { items: ActionItem[] }) {
  return (
    <section
      aria-labelledby="manager-actions"
      className="flex flex-col gap-1 rounded-card bg-card px-3 py-5 md:px-5 md:py-7"
    >
      <h2 id="manager-actions" className="px-2 pb-3 text-heading">
        Perlu tindakan
      </h2>
      {items.length === 0 ? (
        <p className="px-2 text-body text-muted-foreground">Tidak ada yang menunggu. Tim aman.</p>
      ) : (
        <ul className="flex flex-col gap-1">
          {items.map((item) => {
            const { icon: Icon, tone } = icons[item.kind];
            return (
              <li key={item.key}>
                <Link
                  href={item.href}
                  className="flex items-center gap-3.5 rounded-field px-2 py-3.5 outline-none hover:bg-secondary/60 focus-visible:outline-2 focus-visible:outline-ring"
                >
                  <span className="flex size-9 shrink-0 items-center justify-center rounded-control bg-background">
                    <Icon className={cn("size-4.5", tone)} aria-hidden />
                  </span>
                  <span className="flex min-w-0 flex-1 flex-col gap-0.5">
                    <span className="font-semibold text-sm">{item.title}</span>
                    <span className="text-faint-foreground text-xs">{item.detail}</span>
                  </span>
                  <span className="shrink-0 font-semibold text-caption">{item.cta}</span>
                </Link>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
