import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { ModalComponent } from '@common/components/modal/modal.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, ModalComponent],
  templateUrl: './app.component.html',
})
export class AppComponent {}
