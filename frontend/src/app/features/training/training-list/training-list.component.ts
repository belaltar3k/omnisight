import { Component, inject } from "@angular/core";
import { ButtonComponent } from "@common/components/button/button.component";
import { TrainingService } from "@core/services";
import {AsyncPipe} from "@angular/common";
import {BtnStylesEnum} from "@shared/enums";

@Component({
  selector: "app-training-list",
  standalone: true,
  templateUrl: "./training-list.component.html",
    imports: [ButtonComponent, AsyncPipe],
})
export class TrainingListComponent {
  private readonly trainingService = inject(TrainingService);

  jobs$ = this.trainingService.getJobs();

  ngOnInit() {}

  statusClass(s: string): string {
    const statusMap: { [key: string]: string } = {
      running: "bg-blue-500/20 text-blue-400",
      completed: "bg-emerald-500/20 text-emerald-400",
      failed: "bg-red-500/20 text-red-400",
    };
    return statusMap[s] ?? "bg-slate-500/20 text-slate-400";
  }

  protected readonly BtnStylesEnum = BtnStylesEnum;
}