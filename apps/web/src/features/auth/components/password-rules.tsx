import { Circle, CircleCheck, Info } from "lucide-react";
import { cn } from "@/shared/lib/cn";
import { passwordRules } from "../auth";

/** Live checklist under the new-password field (A3, A4). */
export function PasswordRules({
  id,
  password,
  hint,
}: {
  id: string;
  password: string;
  hint?: string;
}) {
  return (
    <ul id={id} className="flex flex-col gap-2 rounded-field bg-card p-3.5">
      {passwordRules(password).map((rule) => {
        const Icon = rule.met ? CircleCheck : Circle;
        return (
          <li
            key={rule.label}
            className={cn(
              "flex items-center gap-2 font-semibold text-caption",
              rule.met ? "text-success" : "text-faint-foreground",
            )}
          >
            <Icon aria-hidden className="size-4" />
            {rule.label}
            <span className="sr-only">{rule.met ? ", terpenuhi" : ", belum terpenuhi"}</span>
          </li>
        );
      })}
      {hint && (
        <li className="flex items-center gap-2 font-semibold text-caption text-faint-foreground">
          <Info aria-hidden className="size-4" />
          {hint}
        </li>
      )}
    </ul>
  );
}
