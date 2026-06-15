import { Component, input } from "@angular/core";

@Component({
  selector: "app-metric-card",
  standalone: true,
  templateUrl: "./metric-card.component.html",
})
export class MetricCardComponent {
  label = input("");
  value = input("");
  icon = input("");
  trend = input("");
  trendUp = input(true);
}
