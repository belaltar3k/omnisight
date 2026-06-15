import { Component, inject, OnDestroy, OnInit, signal } from '@angular/core';
import { ButtonComponent } from "@common/components/button/button.component";
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';

interface EventItem {
  title: string;
  time: string;
  iconColor: string;
  thumbGradientClass: string;
  iconSvg: SafeHtml;
}

@Component({
  selector: 'app-events-list',
  standalone: true,
  imports: [ButtonComponent],
  templateUrl: './events-list.component.html',
  styles: [`:host { display: contents; }`],
})
export class EventsListComponent implements OnInit, OnDestroy {
  private sanitizer = inject(DomSanitizer);

  readonly reducedMotion = signal(false);
  private motionQuery: MediaQueryList | undefined;
  private motionListener: ((e: MediaQueryListEvent) => void) | undefined;

  ngOnInit(): void {
    this.motionQuery = globalThis.matchMedia('(prefers-reduced-motion: reduce)');
    this.reducedMotion.set(this.motionQuery.matches);
    this.motionListener = (e) => this.reducedMotion.set(e.matches);
    this.motionQuery.addEventListener('change', this.motionListener);
  }

  ngOnDestroy(): void {
    if (this.motionQuery && this.motionListener) {
      this.motionQuery.removeEventListener('change', this.motionListener);
    }
  }
  private safe = (s: string): SafeHtml => this.sanitizer.bypassSecurityTrustHtml(s);

  events: EventItem[] = [
    { title: 'Smoke Detected', time: '02/20 PM - Ware House1', iconColor: 'text-orange-400', thumbGradientClass: 'bg-gradient-to-br from-[#431407] to-[#7f1d1d]', iconSvg: this.safe(`<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z"/></svg>`) },
    { title: 'Temperature Warning', time: '02/20 PM - Ware House1', iconColor: 'text-yellow-400', thumbGradientClass: 'bg-gradient-to-br from-[#451a03] to-[#78350f]', iconSvg: this.safe(`<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 14.76V3.5a2.5 2.5 0 0 0-5 0v11.26a4.5 4.5 0 1 0 5 0z"/></svg>`) },
    { title: 'Blacklisted Face Recognized', time: '02/20 PM - Ware House1', iconColor: 'text-red-400', thumbGradientClass: 'bg-gradient-to-br from-slate-800 to-slate-700', iconSvg: this.safe(`<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>`) },
    { title: 'Motion Detected', time: '02/20 PM - Ware House1', iconColor: 'text-blue-400', thumbGradientClass: 'bg-gradient-to-br from-[#0c1a3a] to-[#1e3a5f]', iconSvg: this.safe(`<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>`) },
    { title: 'Operator Login', time: '12/7 PM', iconColor: 'text-green-400', thumbGradientClass: 'bg-gradient-to-br from-[#052e16] to-[#14532d]', iconSvg: this.safe(`<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"/><polyline points="10 17 15 12 10 7"/><line x1="15" x2="3" y1="12" y2="12"/></svg>`) },
    { title: 'Motion Detected', time: '01/20 PM - Parking Garage1', iconColor: 'text-blue-400', thumbGradientClass: 'bg-gradient-to-br from-[#0c1a3a] to-[#1e3a5f]', iconSvg: this.safe(`<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>`) },
  ];
}
