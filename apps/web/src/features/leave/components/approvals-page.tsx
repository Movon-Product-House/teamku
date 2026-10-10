"use client";

import { useEffect, useState } from "react";
import { errorMessage } from "@/shared/api/client";
import { formatDate } from "@/shared/lib/format";
import { Button } from "@/shared/ui/button";
import { notify } from "@/shared/ui/notifications";
import { useApprovals } from "../api";
import { type ApprovalFilter, countApprovals, filterApprovals } from "../approvals";
import { type ApprovalDecision, type ApprovalRequest, leaveStatusLabels } from "../types";
import { DecisionDialog } from "./decision-dialog";

const FILTERS: [ApprovalFilter, string][] = [
  ["pending", "Menunggu"],
  ["approved", "Disetujui"],
  ["rejected", "Ditolak"],
  ["all", "Semua"],
];

export function ApprovalsPage() {
  const approvals = useApprovals();
  const [filter, setFilter] = useState<ApprovalFilter>("pending");
  const [selected, setSelected] = useState<{
    request: ApprovalRequest;
    decision: ApprovalDecision;
  } | null>(null);

  useEffect(() => {
    if (approvals.error)
      notify({
        type: "error",
        title: "Tidak dapat memuat persetujuan",
        message: errorMessage(approvals.error, "Data persetujuan gagal dimuat."),
      });
  }, [approvals.error]);

  const items = approvals.data ?? [];
  const visible = filterApprovals(items, filter);

  return (
    <>
      <section className="page-heading">
        <div>
          <p className="eyebrow">Approval inbox</p>
          <h1>Persetujuan</h1>
          <p>Tinjau permohonan tim sesuai cakupan dan simpan keputusan dengan catatan.</p>
        </div>
        <Button
          variant="outline"
          onClick={() => approvals.refetch()}
          disabled={approvals.isFetching}
        >
          {approvals.isFetching ? "Memuat…" : "Perbarui data"}
        </Button>
      </section>
      <div className="filter-tabs" role="tablist">
        {FILTERS.map(([key, label]) => (
          <button
            type="button"
            role="tab"
            aria-selected={filter === key}
            className={filter === key ? "active" : ""}
            onClick={() => setFilter(key)}
            key={key}
          >
            {label}
            <span>{countApprovals(items, key)}</span>
          </button>
        ))}
      </div>
      <div className="card table-card">
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>Karyawan</th>
                <th>Jenis</th>
                <th>Tanggal</th>
                <th>Durasi</th>
                <th>Alasan</th>
                <th>Status</th>
                <th>Aksi</th>
              </tr>
            </thead>
            <tbody>
              {visible.map((item) => (
                <tr key={item.id}>
                  <td>
                    <b>{item.employee_name}</b>
                    <small>{item.department}</small>
                  </td>
                  <td>Cuti tahunan</td>
                  <td>
                    {formatDate(item.start)} — {formatDate(item.end)}
                  </td>
                  <td>{item.days} hari kerja</td>
                  <td>
                    {item.reason}
                    {item.approver_comment && <small>Catatan: {item.approver_comment}</small>}
                  </td>
                  <td>
                    <span className={`status ${item.status}`}>
                      {leaveStatusLabels[item.status] ?? item.status}
                    </span>
                  </td>
                  <td>
                    {item.status === "pending" ? (
                      <div className="flex gap-2">
                        <Button
                          size="sm"
                          onClick={() => setSelected({ request: item, decision: "approved" })}
                        >
                          Setujui
                        </Button>
                        <Button
                          size="sm"
                          variant="destructive"
                          onClick={() => setSelected({ request: item, decision: "rejected" })}
                        >
                          Tolak
                        </Button>
                      </div>
                    ) : (
                      <span className="muted">Selesai</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {approvals.isPending && (
          <p role="status" className="p-6 text-center text-muted-foreground text-sm">
            Memuat permohonan…
          </p>
        )}
        {approvals.isSuccess && visible.length === 0 && (
          <div className="feature-empty">
            <span>✓</span>
            <h2>Tidak ada permohonan di sini</h2>
            <p>Semua permohonan pada status ini sudah tertangani.</p>
          </div>
        )}
      </div>
      {selected && (
        <DecisionDialog
          request={selected.request}
          decision={selected.decision}
          onClose={() => setSelected(null)}
        />
      )}
    </>
  );
}
