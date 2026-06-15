import { Component, input, computed } from "@angular/core";

export type Priority = "critical" | "high" | "medium" | "low";

const PRIORITY_CONFIG: Record<
  Priority,
  { label: string; classes: string; icon: string }
> = {
  critical: {
    label: "Critical",
    classes: "bg-red-500/20 text-red-400 border-red-500/30",
    icon: "!",
  },
  high: {
    label: "High",
    classes: "bg-orange-500/20 text-orange-400 border-orange-500/30",
    icon: "↑",
  },
  medium: {
    label: "Medium",
    classes: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
    icon: "—",
  },
  low: {
    label: "Low",
    classes: "bg-slate-500/20 text-slate-400 border-slate-500/30",
    icon: "↓",
  },
};

@Component({
  selector: "app-priority-badge",
  standalone: true,
  templateUrl: "./priority-badge.component.html",
})
export class PriorityBadgeComponent {
  priority = input("medium" as Priority);
  config = computed(() => PRIORITY_CONFIG[this.priority()]);
}
