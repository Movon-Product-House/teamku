"use client";

import { type FormEvent, useId, useState } from "react";
import { errorMessage } from "@/shared/api/client";
import { formatDate } from "@/shared/lib/format";
import { Button } from "@/shared/ui/button";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/shared/ui/dialog";
import { notify } from "@/shared/ui/notifications";
import { Textarea } from "@/shared/ui/textarea";
import { useDecideApproval } from "../api";
import { defaultDecisionComment, validateDecisionComment } from "../approvals";
import type { ApprovalDecision, ApprovalRequest } from "../types";

type Props = { request: ApprovalRequest; decision: ApprovalDecision; onClose: () => void };

export function DecisionDialog({ request, decision, onClose }: Props) {
  const [comment, setComment] = useState(() => defaultDecisionComment(decision));
  const [error, setError] = useState<string | null>(null);
  const decide = useDecideApproval();
  const commentId = useId();
  const errorId = useId();
  const approving = decision === "approved";

  function submit(event: FormEvent) {
    event.preventDefault();
    const invalid = validateDecisionComment(comment);
    setError(invalid);
    if (invalid) return;
    decide.mutate(
      { id: request.id, decision, comment },
      {
        onSuccess: (result) => {
          notify({
            type: "success",
            title: "Keputusan tersimpan",
            message:
              result.calendar_sync_status === "failed"
                ? "Permohonan diproses, tetapi event Google Calendar gagal dibuat."
                : `Permohonan ${request.employee_name} berhasil diproses.`,
          });
          onClose();
        },
        onError: (reason) =>
          notify({
            type: "error",
            title: "Keputusan gagal disimpan",
            message: errorMessage(reason, "Keputusan gagal disimpan"),
          }),
      },
    );
  }

  return (
    // Selama menyimpan, dialog tidak bisa ditutup agar hasil mutasi tidak hilang dari pandangan.
    <Dialog open onOpenChange={(open) => !open && !decide.isPending && onClose()}>
      <DialogContent className="sm:max-w-md" showCloseButton={!decide.isPending}>
        <form onSubmit={submit} className="grid gap-4">
          <DialogHeader>
            <p className="font-semibold text-muted-foreground text-xs uppercase tracking-wider">
              Konfirmasi keputusan
            </p>
            <DialogTitle className="font-semibold text-lg leading-snug">
              {approving ? "Setujui" : "Tolak"} permohonan {request.employee_name}?
            </DialogTitle>
            <DialogDescription>
              {formatDate(request.start)} — {formatDate(request.end)} · {request.days} hari kerja
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-2">
            <label htmlFor={commentId} className="font-semibold text-sm">
              Catatan keputusan
            </label>
            <Textarea
              id={commentId}
              rows={4}
              value={comment}
              onChange={(event) => setComment(event.target.value)}
              placeholder="Jelaskan keputusan untuk karyawan"
              aria-invalid={error !== null}
              aria-describedby={error ? errorId : undefined}
            />
            {error && (
              <p id={errorId} role="alert" className="text-destructive text-sm">
                {error}
              </p>
            )}
          </div>
          <DialogFooter>
            <DialogClose asChild>
              <Button type="button" variant="outline" disabled={decide.isPending}>
                Batal
              </Button>
            </DialogClose>
            <Button
              type="submit"
              variant={approving ? "default" : "destructive"}
              disabled={decide.isPending}
            >
              {decide.isPending ? "Menyimpan…" : "Simpan keputusan"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
