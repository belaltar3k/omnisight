import { Component, inject } from "@angular/core";
import { AsyncPipe } from "@angular/common";
import { MLModelService } from "@core/services";

@Component({
  selector: "app-model-list",
  standalone: true,
  imports: [AsyncPipe],
  templateUrl: "./model-list.component.html",
})
export class ModelListComponent {
  private readonly mlModelService = inject(MLModelService);

  models$ = this.mlModelService.getModels();
}
