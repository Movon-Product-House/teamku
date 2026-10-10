import type * as React from "react";
import { cn } from "@/shared/lib/cn";

// Kelas kotak isian bersama Input & Textarea (komponen Field di design.pen).
// Teks 16px di mobile agar Safari iOS tidak zoom saat fokus; 15px mulai md.
export const fieldBoxClass =
  "w-full min-w-0 rounded-field border border-input bg-card px-4 text-base font-medium text-foreground transition-[border-color,box-shadow] duration-150 outline-none placeholder:font-normal placeholder:text-faint-foreground focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/10 disabled:cursor-not-allowed disabled:bg-secondary disabled:opacity-60 aria-invalid:border-destructive aria-invalid:ring-3 aria-invalid:ring-destructive/15 md:text-body";

function Input({ className, type, ...props }: React.ComponentProps<"input">) {
  return (
    <input
      type={type}
      data-slot="input"
      className={cn(
        fieldBoxClass,
        "h-13 file:inline-flex file:h-7 file:border-0 file:bg-transparent file:font-semibold file:text-sm",
        className,
      )}
      {...props}
    />
  );
}

export { Input };
