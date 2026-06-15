import { AsyncPipe } from "@angular/common";
import { Component, inject } from "@angular/core";
import { DatasetService } from "@core/services";

@Component({
  selector: "app-dataset-list",
  standalone: true,
  templateUrl: "./dataset-list.component.html",
  imports: [AsyncPipe],
})
export class DatasetListComponent {
  private readonly datasetService = inject(DatasetService);

  datasets$ = this.datasetService.getDatasets();
}
