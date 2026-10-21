import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";
import { cn } from "@/shared/lib/cn";
import { BrandLogo } from "@/shared/ui/brand-logo";

/**
 * v2 auth column (A1–A4). The mockup is mobile only, so desktop keeps the same 390px column,
 * centred on the canvas.
 */
export function AuthLayout({
  title,
  subtitle,
  logo = true,
  back,
  badge,
  children,
}: {
  title: ReactNode;
  subtitle?: ReactNode;
  logo?: boolean;
  /** "Kembali ke login" link above the title (A2). */
  back?: boolean;
  /** Something between the logo and the title, e.g. the invite card or the mail icon. */
  badge?: ReactNode;
  children: ReactNode;
}) {
  return (
    <main data-surface="v2" className="flex min-h-dvh justify-center bg-background lg:items-center">
      <div className="flex w-full max-w-97.5 flex-col gap-7 px-6 pt-7 pb-8 lg:py-16">
        {logo && <BrandLogo variant="black" className="h-7.75 w-auto self-start" />}
        {back && <BackToLogin className="self-start" />}
        {badge}
        <div className="flex flex-col gap-2">
          <h1 className="font-display text-title-sm">{title}</h1>
          {subtitle && <p className="text-body text-muted-foreground">{subtitle}</p>}
        </div>
        {children}
      </div>
    </main>
  );
}

export function BackToLogin({ className, icon = true }: { className?: string; icon?: boolean }) {
  return (
    <Link
      href="/login"
      className={cn(
        "inline-flex items-center gap-1.5 rounded-control font-semibold text-sm outline-none hover:underline focus-visible:outline-2 focus-visible:outline-ring",
        className,
      )}
    >
      {icon && <ArrowLeft aria-hidden className="size-4.5" />}
      Kembali ke login
    </Link>
  );
}

/** Shown while a token link is being checked (A3, A4). */
export function AuthChecking({ message }: { message: string }) {
  return (
    <main
      data-surface="v2"
      role="status"
      className="flex min-h-dvh items-center justify-center gap-3 bg-background text-body text-muted-foreground"
    >
      <span
        aria-hidden
        className="size-4 animate-spin rounded-full border-2 border-border border-t-foreground"
      />
      {message}
    </main>
  );
}
