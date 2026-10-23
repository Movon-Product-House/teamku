"use client";

import type { UseQueryResult } from "@tanstack/react-query";
import { errorMessage } from "@/shared/api/client";
import { cn } from "@/shared/lib/cn";
import { Alert, AlertDescription, AlertTitle } from "@/shared/ui/alert";
import { Button } from "@/shared/ui/button";

/** Loading, error and success for one card; `null` data is each card's own empty state. */
export function Loaded<T>({
  query,
  label,
  className,
  children,
}: {
  query: UseQueryResult<T>;
  label: string;
  className?: string;
  children: (data: T) => React.ReactNode;
}) {
  if (query.isPending)
    return (
      <div
        role="status"
        aria-label={`Memuat ${label.toLowerCase()}`}
        className={cn("min-h-32 animate-pulse rounded-card bg-card", className)}
      />
    );
  if (query.isError)
    return (
      <Alert variant="destructive" className={cn("rounded-card p-5", className)}>
        <AlertTitle>{label} belum dapat dimuat</AlertTitle>
        <AlertDescription className="flex flex-col items-start gap-2">
          {errorMessage(query.error, "Coba lagi sebentar lagi.")}
          <Button size="sm" variant="outline" onClick={() => query.refetch()}>
            Coba lagi
          </Button>
        </AlertDescription>
      </Alert>
    );
  return children(query.data);
}
