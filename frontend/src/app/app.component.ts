import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { LoadingScreenComponent } from '@common/components/loading-screen/loading-screen.component';
import { ModalComponent } from '@common/components/modal/modal.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, LoadingScreenComponent, ModalComponent],
  templateUrl: './app.component.html',
})
export class AppComponent {}
