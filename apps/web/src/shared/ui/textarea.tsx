import type * as React from "react";
import { cn } from "@/shared/lib/cn";
import { fieldBoxClass } from "./input";

function Textarea({ className, ...props }: React.ComponentProps<"textarea">) {
  return (
    <textarea
      data-slot="textarea"
      className={cn(fieldBoxClass, "field-sizing-content min-h-24 py-3.5", className)}
      {...props}
    />
  );
}

export { Textarea };
