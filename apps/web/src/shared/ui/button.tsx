import { cva, type VariantProps } from "class-variance-authority";
import { Slot } from "radix-ui";
import type * as React from "react";
import { cn } from "@/shared/lib/cn";

// v2: satu tombol `default` (hitam) per layar; aksi lain `secondary`/`outline`/`ghost`.
// Ukuran `default` = desktop (42px), `lg` = tombol utama mobile (52px).
const buttonVariants = cva(
  "group/button inline-flex shrink-0 items-center justify-center rounded-control border border-transparent bg-clip-padding text-sm font-semibold whitespace-nowrap transition-[color,background-color,border-color,transform] duration-150 ease-out outline-none select-none focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-solid focus-visible:outline-ring active:not-aria-[haspopup]:translate-y-px disabled:pointer-events-none disabled:opacity-50 aria-invalid:border-destructive [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground hover:bg-primary/85",
        secondary: "bg-card text-foreground hover:bg-secondary aria-expanded:bg-secondary",
        outline:
          "border-border bg-card text-foreground hover:bg-secondary aria-expanded:bg-secondary",
        ghost: "text-foreground hover:bg-secondary aria-expanded:bg-secondary",
        destructive: "bg-destructive-muted text-destructive hover:bg-destructive/15",
        link: "text-foreground underline underline-offset-4 hover:text-muted-foreground",
      },
      size: {
        default: "h-10.5 gap-2 px-4",
        sm: "h-9 gap-1.5 px-3",
        lg: "h-13 gap-2 rounded-field px-5 text-body font-bold [&_svg:not([class*='size-'])]:size-[18px]",
        icon: "size-10.5",
        "icon-sm": "size-8",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  },
);

function Button({
  className,
  variant = "default",
  size = "default",
  asChild = false,
  ...props
}: React.ComponentProps<"button"> &
  VariantProps<typeof buttonVariants> & {
    asChild?: boolean;
  }) {
  const Comp = asChild ? Slot.Root : "button";

  return (
    <Comp
      data-slot="button"
      data-variant={variant}
      data-size={size}
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  );
}

export { Button, buttonVariants };
