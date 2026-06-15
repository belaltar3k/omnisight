import { Component, input, computed } from "@angular/core";

export type IncidentStatus =
  | "new"
  | "vlm_verifying"
  | "acknowledged"
  | "investigating"
  | "dispatched"
  | "on_scene"
  | "resolved"
  | "false_positive"
  | "escalated";

const STATUS_CONFIG: Record<
  IncidentStatus,
  { label: string; classes: string }
> = {
  new: {
    label: "New",
    classes: "bg-blue-500/20 text-blue-400 border-blue-500/30",
  },
  vlm_verifying: {
    label: "VLM Verifying",
    classes: "bg-purple-500/20 text-purple-400 border-purple-500/30",
  },
  acknowledged: {
    label: "Acknowledged",
    classes: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
  },
  investigating: {
    label: "Investigating",
    classes: "bg-orange-500/20 text-orange-400 border-orange-500/30",
  },
  dispatched: {
    label: "Dispatched",
    classes: "bg-indigo-500/20 text-indigo-400 border-indigo-500/30",
  },
  on_scene: {
    label: "On Scene",
    classes: "bg-cyan-500/20 text-cyan-400 border-cyan-500/30",
  },
  resolved: {
    label: "Resolved",
    classes: "bg-green-500/20 text-green-400 border-green-500/30",
  },
  false_positive: {
    label: "False Positive",
    classes: "bg-slate-500/20 text-slate-400 border-slate-500/30",
  },
  escalated: {
    label: "Escalated",
    classes: "bg-red-500/20 text-red-400 border-red-500/30",
  },
};

@Component({
  selector: "app-status-badge",
  standalone: true,
  templateUrl: "./status-badge.component.html",
})
export class StatusBadgeComponent {
  status = input("new" as IncidentStatus);
  config = computed(() => STATUS_CONFIG[this.status()]);
}
