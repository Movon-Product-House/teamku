"use client";
import { useEffect, useMemo, useState } from "react";
import { type LeaveStatus, leaveStatusLabels } from "@/features/leave/types";
import { api } from "@/shared/api/client";
import { formatDate } from "@/shared/lib/format";
import { NotificationDialog, type NotificationDialogState } from "@/shared/ui/notification-dialog";

type Request = {
  id: string;
  start: string;
  end: string;
  reason: string;
  days: number;
  status: LeaveStatus;
  approver_comment?: string;
};
type Data = {
  items: Request[];
  balance: { annual_days: number; used_days: number; remaining_days: number };
};

export default function TimeOff() {
  const initial = useMemo(() => futureDate(7), []);
  const [start, setStart] = useState(initial),
    [end, setEnd] = useState(initial),
    [reason, setReason] = useState(""),
    [data, setData] = useState<Data>(),
    [notification, setNotification] = useState<NotificationDialogState | null>(null),
    [busy, setBusy] = useState(false);
  const notify = (type: NotificationDialogState["type"], title: string, message: string) =>
    setNotification({ type, title, message });
  const load = () =>
    api<Data>("/leave-requests", {})
      .then((result) => setData(result))
      .catch((reason) =>
        notify(
          "error",
          "Tidak dapat memuat cuti",
          reason instanceof Error ? reason.message : "Data cuti gagal dimuat.",
        ),
      );
  useEffect(() => {
    load();
  }, []);
  const preview = workingDays(start, end);
  async function submit() {
    if (reason.trim().length < 4) {
      notify("error", "Alasan belum lengkap", "Jelaskan alasan cuti minimal 4 karakter.");
      return;
    }
    setBusy(true);
    try {
      await api("/leave-requests", {
        method: "POST",
        body: JSON.stringify({ start, end, reason }),
      });
      setReason("");
      notify("success", "Permohonan terkirim", "Permohonan berhasil dikirim ke atasan.");
      await load();
    } catch (cause) {
      notify(
        "error",
        "Permohonan gagal dikirim",
        cause instanceof Error ? cause.message : "Permohonan gagal dikirim",
      );
    } finally {
      setBusy(false);
    }
  }
  async function cancel(id: string) {
    setBusy(true);
    try {
      await api(`/leave-requests/${id}/cancel`, { method: "POST" });
      notify(
        "success",
        "Permohonan dibatalkan",
        "Permohonan berhasil dibatalkan dan saldo disesuaikan.",
      );
      await load();
    } catch (cause) {
      notify(
        "error",
        "Pembatalan gagal",
        cause instanceof Error ? cause.message : "Pembatalan gagal",
      );
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <NotificationDialog notification={notification} onClose={() => setNotification(null)} />
      <section className="page-heading">
        <div>
          <p className="eyebrow">Employee self service</p>
          <h1>Cuti & izin</h1>
          <p>Rencanakan waktu istirahat, lihat dampak saldo, dan pantau keputusan atasan.</p>
        </div>
      </section>
      <section className="leave-balance-grid">
        <article className="balance-card primary">
          <span>Sisa cuti tahunan</span>
          <strong>{data?.balance.remaining_days ?? "-"}</strong>
          <small>hari kerja tersedia</small>
        </article>
        <article className="balance-card">
          <span>Hak tahun ini</span>
          <strong>{data?.balance.annual_days ?? "-"}</strong>
          <small>hari kerja</small>
        </article>
        <article className="balance-card">
          <span>Sudah digunakan</span>
          <strong>{data?.balance.used_days ?? "-"}</strong>
          <small>hari disetujui</small>
        </article>
      </section>
      <section className="two-column-feature">
        <article className="panel request-form">
          <p className="eyebrow">Permohonan baru</p>
          <h2>Ajukan cuti tahunan</h2>
          <div className="date-grid">
            <label>
              Tanggal mulai
              <input type="date" value={start} onChange={(event) => setStart(event.target.value)} />
            </label>
            <label>
              Tanggal selesai
              <input
                type="date"
                min={start}
                value={end}
                onChange={(event) => setEnd(event.target.value)}
              />
            </label>
          </div>
          <div className="impact-preview">
            <span>Dampak saldo</span>
            <b>{preview} hari kerja</b>
            <small>Perhitungan final mengikuti kalender dan kebijakan perusahaan.</small>
          </div>
          <label>
            Alasan
            <textarea
              rows={4}
              value={reason}
              onChange={(event) => setReason(event.target.value)}
              placeholder="Contoh: acara keluarga di luar kota"
            />
          </label>
          <button className="primary-action" disabled={busy || preview < 1} onClick={submit}>
            {busy ? "Mengirim…" : "Kirim untuk persetujuan"}
          </button>
        </article>
        <article className="panel request-history">
          <div className="panel-head">
            <div>
              <p className="eyebrow">Riwayat</p>
              <h2>Permohonan saya</h2>
            </div>
            <button className="text-button" onClick={load}>
              Perbarui
            </button>
          </div>
          {data?.items.length ? (
            data.items.map((item) => (
              <div className="request-item" key={item.id}>
                <div>
                  <b>
                    {formatDate(item.start)} — {formatDate(item.end)}
                  </b>
                  <small>
                    {item.days} hari kerja · {item.reason}
                  </small>
                  {item.approver_comment && <small>Catatan atasan: {item.approver_comment}</small>}
                </div>
                <div>
                  <span className={`status ${item.status}`}>
                    {leaveStatusLabels[item.status] || item.status}
                  </span>
                  {["pending", "approved"].includes(item.status) && (
                    <button disabled={busy} onClick={() => cancel(item.id)}>
                      Batalkan
                    </button>
                  )}
                </div>
              </div>
            ))
          ) : (
            <div className="feature-empty compact">
              <span>◎</span>
              <h2>Belum ada permohonan</h2>
              <p>Permohonan yang dikirim akan muncul di sini.</p>
            </div>
          )}
        </article>
      </section>
    </>
  );
}
function futureDate(days: number) {
  const value = new Date();
  value.setDate(value.getDate() + days);
  return value.toISOString().slice(0, 10);
}
function workingDays(start: string, end: string) {
  if (!start || !end || end < start) return 0;
  let total = 0,
    current = new Date(`${start}T00:00:00`),
    last = new Date(`${end}T00:00:00`);
  while (current <= last) {
    if (current.getDay() !== 0 && current.getDay() !== 6) total++;
    current.setDate(current.getDate() + 1);
  }
  return total;
}
