import { Component, input, InputSignal } from '@angular/core';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-anchor',
  standalone: true,
  imports: [RouterLink],
  templateUrl: './anchor.component.html',
})
export class AnchorComponent {
  message: InputSignal<string> = input('');
  link: InputSignal<string> = input('');
}
