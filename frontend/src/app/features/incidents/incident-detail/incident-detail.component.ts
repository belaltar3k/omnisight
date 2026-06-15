import { Component, inject, OnInit, signal } from "@angular/core";
import { ActivatedRoute, RouterLink } from "@angular/router";
import { DatePipe, DecimalPipe } from "@angular/common";
import { ButtonComponent } from "@common/components/button/button.component";
import { StatusBadgeComponent } from "@common/components/status-badge/status-badge.component";
import { PriorityBadgeComponent } from "@common/components/priority-badge/priority-badge.component";
import { IncidentService } from "@core/services";
import { BtnStylesEnum, IncidentStatus } from "@shared/enums";
import { IIncident, IIncidentTimelineEvent } from "@shared/interfaces/incident";
import { ToastrService } from "ngx-toastr";

@Component({
  selector: "app-incident-detail",
  standalone: true,
  imports: [RouterLink, DatePipe, DecimalPipe, ButtonComponent, StatusBadgeComponent, PriorityBadgeComponent],
  templateUrl: "./incident-detail.component.html",
})
export class IncidentDetailComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly incidentService = inject(IncidentService);
  private readonly toastr = inject(ToastrService);

  readonly incident = signal<IIncident | null>(null);
  readonly timeline = signal<IIncidentTimelineEvent[]>([]);
  readonly isLoading = signal(true);
  protected readonly BtnStylesEnum = BtnStylesEnum;
  protected readonly IncidentStatus = IncidentStatus;

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id');
    if (!id) return;

    this.incidentService.getIncidentById(id).subscribe({
      next: (inc) => {
        this.incident.set(inc);
        this.isLoading.set(false);
      },
      error: () => this.isLoading.set(false),
    });

    this.incidentService.getTimeline(id).subscribe({
      next: (events) => this.timeline.set(events),
    });
  }

  acknowledge(): void {
    const inc = this.incident();
    if (!inc) return;
    this.incidentService.acknowledgeIncident(inc.incidentId).subscribe({
      next: (updated) => {
        this.incident.set(updated);
        this.toastr.success("Incident acknowledged");
      },
    });
  }

  escalate(): void {
    const inc = this.incident();
    if (!inc) return;
    this.incidentService.escalateIncident(inc.incidentId).subscribe({
      next: (updated) => {
        this.incident.set(updated);
        this.toastr.warning("Incident escalated");
      },
    });
  }

  resolve(): void {
    const inc = this.incident();
    if (!inc) return;
    this.incidentService.resolveIncident(inc.incidentId, { resolutionNotes: 'Resolved via dashboard' }).subscribe({
      next: (updated) => {
        this.incident.set(updated);
        this.toastr.success("Incident resolved");
      },
    });
  }

  markFalsePositive(): void {
    const inc = this.incident();
    if (!inc) return;
    this.incidentService.markFalsePositive(inc.incidentId, { falsePositiveReason: 'Marked false positive via dashboard' }).subscribe({
      next: (updated) => {
        this.incident.set(updated);
        this.toastr.info("Marked as false positive");
      },
    });
  }

  fusionBars(inc: IIncident): { name: string; score: number }[] {
    if (!inc.fusionScores) return [];
    const s = inc.fusionScores;
    return [
      { name: 'MIL', score: s.mil },
      { name: 'Flow', score: s.flow },
      { name: 'YOLO', score: s.yolo },
      { name: 'Audio', score: s.audio },
      { name: 'Rules', score: s.rules },
      { name: 'Pose', score: s.pose },
    ];
  }

  confidenceWidth(score: number): string {
    if (score >= 0.875) return 'w-full';
    if (score >= 0.625) return 'w-3/4';
    if (score >= 0.375) return 'w-1/2';
    if (score > 0) return 'w-1/4';
    return 'w-0';
  }

  canAcknowledge(inc: IIncident): boolean {
    return inc.status === IncidentStatus.New || inc.status === IncidentStatus.VlmVerifying;
  }

  canEscalate(inc: IIncident): boolean {
    return inc.status === IncidentStatus.Acknowledged || inc.status === IncidentStatus.Investigating;
  }

  canResolve(inc: IIncident): boolean {
    return inc.status !== IncidentStatus.Resolved && inc.status !== IncidentStatus.FalsePositive;
  }

  timelineEventColor(eventType: string): string {
    if (eventType.includes('creat')) return 'bg-blue-500';
    if (eventType.includes('vlm')) return 'bg-violet-500';
    if (eventType.includes('acknowledge')) return 'bg-yellow-500';
    if (eventType.includes('escalat')) return 'bg-red-500';
    if (eventType.includes('resolv')) return 'bg-emerald-500';
    return 'bg-slate-500';
  }
}
