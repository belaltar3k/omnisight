import { inject, Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { analyticsApiEndpoints } from '@environments';

@Injectable({ providedIn: 'root' })
export class AnalyticsService {
  private http = inject(HttpClient);

  getDashboard(): Observable<any> {
    return this.http.get(analyticsApiEndpoints.dashboard);
  }

  getIncidentStats(dateFrom: string, dateTo: string): Observable<any> {
    return this.http.get(analyticsApiEndpoints.incidentStats, {
      params: { date_from: dateFrom, date_to: dateTo },
    });
  }

  getIncidentTrends(dateFrom: string, dateTo: string, interval = 'D'): Observable<any> {
    return this.http.get(analyticsApiEndpoints.incidentTrends, {
      params: { date_from: dateFrom, date_to: dateTo, interval },
    });
  }

  getResponseTimes(dateFrom: string, dateTo: string): Observable<any> {
    return this.http.get(analyticsApiEndpoints.responseTimes, {
      params: { date_from: dateFrom, date_to: dateTo },
    });
  }

  getCameraPerformance(dateFrom: string, dateTo: string): Observable<any> {
    return this.http.get(analyticsApiEndpoints.cameraPerformance, {
      params: { date_from: dateFrom, date_to: dateTo },
    });
  }

  getHeatmap(dateFrom: string, dateTo: string): Observable<any> {
    return this.http.get(analyticsApiEndpoints.heatmap, {
      params: { date_from: dateFrom, date_to: dateTo },
    });
  }

  getSurveillanceSummary(): Observable<any> {
    return this.http.get(analyticsApiEndpoints.surveillanceSummary);
  }

  getSurveillanceLatest(): Observable<any> {
    return this.http.get(analyticsApiEndpoints.surveillanceLatest);
  }

  getCrowdMetrics(hours = 1): Observable<any> {
    return this.http.get(analyticsApiEndpoints.surveillanceCrowd, { params: { hours } });
  }

  getTrafficMetrics(hours = 1): Observable<any> {
    return this.http.get(analyticsApiEndpoints.surveillanceTraffic, { params: { hours } });
  }

  generateReport(body: any): Observable<any> {
    return this.http.post(analyticsApiEndpoints.generateReport, body);
  }

  getVlmAnalyses(params?: any): Observable<any> {
    return this.http.get(analyticsApiEndpoints.vlmAnalyses, { params });
  }

  getVlmAnalysis(id: string): Observable<any> {
    return this.http.get(analyticsApiEndpoints.vlmAnalysis(id));
  }

  getVlmSummary(hours = 24): Observable<any> {
    return this.http.get(analyticsApiEndpoints.vlmSummary, { params: { hours } });
  }
}
