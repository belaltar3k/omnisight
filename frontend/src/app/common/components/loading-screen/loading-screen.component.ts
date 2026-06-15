import {
  Component, inject, signal, effect, ViewChild, ElementRef, AfterViewInit, OnDestroy, OnInit,
} from '@angular/core';
import { LoadingService } from '../../../core/services/loading.service';

@Component({
  selector: 'app-loading-screen',
  standalone: true,
  templateUrl: './loading-screen.component.html',
  styleUrl: './loading-screen.component.css',
})
export class LoadingScreenComponent implements AfterViewInit, OnInit, OnDestroy {
  @ViewChild('videoEl') videoEl?: ElementRef<HTMLVideoElement>;

  private loadingService = inject(LoadingService);

  visible = signal(false);
  isOpaque = signal(false);
  dots = [0, 1, 2];
  readonly reducedMotion = signal(false);
  private motionQuery: MediaQueryList | undefined;
  private motionListener: ((e: MediaQueryListEvent) => void) | undefined;

  private fadeOutTimer?: ReturnType<typeof setTimeout>;
  private fadeInTimer?: ReturnType<typeof setTimeout>;

  constructor() {
    effect(() => {
      if (this.loadingService.isLoading()) this.showOverlay();
      else this.hideOverlay();
    });
  }

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
    clearTimeout(this.fadeOutTimer);
    clearTimeout(this.fadeInTimer);
  }

  ngAfterViewInit() {
    this.videoEl?.nativeElement.play().catch(() => {});
  }

  private showOverlay() {
    clearTimeout(this.fadeOutTimer);
    this.visible.set(true);
    this.fadeInTimer = setTimeout(() => {
      this.isOpaque.set(true);
      this.videoEl?.nativeElement.play().catch(() => {});
    }, 10);
  }

  private hideOverlay() {
    clearTimeout(this.fadeInTimer);
    this.isOpaque.set(false);
    this.fadeOutTimer = setTimeout(() => {
      this.visible.set(false);
      this.videoEl?.nativeElement.pause();
    }, 650);
  }
}
