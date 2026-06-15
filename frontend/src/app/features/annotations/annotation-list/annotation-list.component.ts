import { AsyncPipe } from "@angular/common";
import { Component, inject } from "@angular/core";
import { AnnotationService } from "@core/services";

@Component({
  selector: "app-annotation-list",
  standalone: true,
  templateUrl: "./annotation-list.component.html",
  imports: [AsyncPipe],
})
export class AnnotationListComponent {
  private readonly annotationService = inject(AnnotationService);

  tasks$ = this.annotationService.getTasks();
}
