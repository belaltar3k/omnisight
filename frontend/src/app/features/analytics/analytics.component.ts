import { Component, signal, inject, computed } from "@angular/core";
import { AsyncPipe, DatePipe, DecimalPipe, JsonPipe, KeyValuePipe, PercentPipe } from "@angular/common";
import { FormsModule } from "@angular/forms";
import { ButtonComponent } from "@common/components/button/button.component";
import { AnalyticsService } from "@core/services";

type AnalyticsTab =
  | "dashboard"
  | "surveillance"
  | "vlm-performance"
  | "incidents"
  | "heatmap"
  | "response-times"
  | "reports";

@Component({
  selector: "app-analytics",
  standalone: true,
  imports: [ButtonComponent, AsyncPipe, DatePipe, DecimalPipe, PercentPipe, JsonPipe, KeyValuePipe, FormsModule],
  templateUrl: "./analytics.component.html",
})
export class AnalyticsComponent {
  private readonly analyticsService = inject(AnalyticsService);

  activeTab = signal<AnalyticsTab>("dashboard");

  tabs: { id: AnalyticsTab; label: string }[] = [
    { id: "dashboard", label: "Dashboard" },
    { id: "surveillance", label: "Surveillance" },
    { id: "vlm-performance", label: "VLM Analyses" },
    { id: "incidents", label: "Incident Stats" },
    { id: "heatmap", label: "Heatmap" },
    { id: "response-times", label: "Response Times" },
    { id: "reports", label: "Reports" },
  ];

  readonly dateFrom = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString();
  readonly dateTo = new Date().toISOString();

  dashboard$ = this.analyticsService.getDashboard();
  surveillanceSummary$ = this.analyticsService.getSurveillanceSummary();
  surveillanceLatest$ = this.analyticsService.getSurveillanceLatest();
  vlmSummary$ = this.analyticsService.getVlmSummary(24);
  vlmAnalyses$ = this.analyticsService.getVlmAnalyses({ hours: 24, limit: 50 });
  incidentStats$ = this.analyticsService.getIncidentStats(this.dateFrom, this.dateTo);
  incidentTrends$ = this.analyticsService.getIncidentTrends(this.dateFrom, this.dateTo, 'D');
  responseTimes$ = this.analyticsService.getResponseTimes(this.dateFrom, this.dateTo);
  heatmap$ = this.analyticsService.getHeatmap(this.dateFrom, this.dateTo);

  reportForm = {
    report_type: 'incident_summary' as 'incident_summary' | 'camera_performance',
    format: 'json' as 'json' | 'csv',
  };
  reportResult = signal<any>(null);
  reportLoading = signal(false);

  get currentTab() {
    return this.tabs.find((t) => t.id === this.activeTab());
  }

  cameraEntries(cameras: Record<string, any>): { code: string; data: any }[] {
    if (!cameras) return [];
    return Object.entries(cameras).map(([code, data]) => ({ code, data }));
  }

  fusionClass(score: number): string {
    if (score > 0.55) return 'text-red-400';
    if (score >= 0.40) return 'text-yellow-400';
    return 'text-emerald-400';
  }

  generateReport(): void {
    this.reportLoading.set(true);
    this.analyticsService.generateReport({
      ...this.reportForm,
      date_from: this.dateFrom,
      date_to: this.dateTo,
    }).subscribe({
      next: (result) => {
        this.reportResult.set(result);
        this.reportLoading.set(false);
      },
      error: () => this.reportLoading.set(false),
    });
  }
}
