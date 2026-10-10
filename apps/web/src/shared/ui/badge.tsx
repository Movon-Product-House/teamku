import { cva, type VariantProps } from "class-variance-authority";
import type * as React from "react";
import { cn } from "@/shared/lib/cn";

// Status = titik berwarna + teks. `soft` (pil berlatar) untuk mobile & kartu,
// `plain` (tanpa latar) untuk tabel dan daftar desktop.
const badgeVariants = cva("inline-flex w-fit shrink-0 items-center gap-1.5 whitespace-nowrap", {
  variants: {
    tone: {
      neutral: "bg-secondary text-faint-foreground",
      success: "bg-success-muted text-success",
      warning: "bg-warning-muted text-warning",
      info: "bg-info-muted text-info",
      destructive: "bg-destructive-muted text-destructive",
    },
    variant: {
      soft: "h-6.5 rounded-full px-2.5 font-bold text-xs",
      plain: "bg-transparent font-semibold text-caption",
    },
  },
  defaultVariants: { tone: "neutral", variant: "soft" },
});

type BadgeProps = React.ComponentProps<"span"> & VariantProps<typeof badgeVariants>;

function Badge({ className, tone, variant, children, ...props }: BadgeProps) {
  return (
    <span
      data-slot="badge"
      data-tone={tone}
      className={cn(badgeVariants({ tone, variant }), className)}
      {...props}
    >
      <span aria-hidden className="size-[7px] shrink-0 rounded-full bg-current" />
      {children}
    </span>
  );
}

export { Badge, badgeVariants };
