import { Component, computed, input } from '@angular/core';

@Component({
  selector: 'app-confidence-bar',
  standalone: true,
  imports: [],
  template: `
    <div class="flex items-center gap-2">
      @if (showLabel()) {
        <span class="text-xs font-mono text-slate-300 w-12 text-right">
          {{ (value() * 100).toFixed(1) }}%
        </span>
      }
      <div class="flex-1 h-2 rounded-full bg-slate-700 overflow-hidden">
        <div
          class="h-full rounded-full transition-all duration-300"
          [class]="barColor()"
          [style.width.%]="value() * 100"
        ></div>
      </div>
    </div>
  `,
})
export class ConfidenceBarComponent {
  readonly value = input.required<number>();
  readonly showLabel = input(true);

  protected readonly barColor = computed(() => {
    const pct = this.value();
    if (pct >= 0.9) return 'bg-green-500';
    if (pct >= 0.75) return 'bg-orange-400';
    if (pct >= 0.5) return 'bg-yellow-400';
    return 'bg-red-500';
  });
}
