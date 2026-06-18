import { Component, inject, OnDestroy, OnInit, signal } from "@angular/core";
import { AsyncPipe, TitleCasePipe } from "@angular/common";
import { ButtonComponent } from "@common/components/button/button.component";
import { EdgeNodeService } from "@core/services";
import { ModalService } from "@core/services/modal.service";
import { BtnStylesEnum } from "@shared/enums";
import { IEdgeNode } from "@shared/interfaces/edge-node";
import { ToastrService } from "ngx-toastr";

@Component({
  selector: "app-edge-node-list",
  standalone: true,
  imports: [TitleCasePipe, AsyncPipe, ButtonComponent],
  templateUrl: "./edge-node-list.component.html",
})
export class EdgeNodeListComponent implements OnInit, OnDestroy {
  private readonly edgeNodeService = inject(EdgeNodeService);
  private readonly modalService = inject(ModalService);
  private readonly toastr = inject(ToastrService);

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

  nodes$ = this.edgeNodeService.getEdgeNodes();
  protected readonly BtnStylesEnum = BtnStylesEnum;

  openAddNodeModal(): void {
    this.modalService.open({
      title: 'Add Edge Node',
      submitLabel: 'Add Edge Node',
      fields: [
        { key: 'name', label: 'Node Name', type: 'text', placeholder: 'Edge Node Cairo 01', required: true },
        { key: 'code', label: 'Code', type: 'text', placeholder: 'EDGE-CAI-01', required: true },
        { key: 'ipAddress', label: 'IP Address', type: 'text', placeholder: '192.168.1.100', required: true },
        { key: 'maxCameras', label: 'Max Cameras', type: 'number', placeholder: '8' },
      ],
      onSubmit: (data) => this.edgeNodeService.createEdgeNode(data as never),
      onSuccess: () => { this.nodes$ = this.edgeNodeService.getEdgeNodes(); },
    });
  }

  openEditNodeModal(node: IEdgeNode): void {
    this.modalService.open({
      title: 'Edit Edge Node',
      submitLabel: 'Save Changes',
      fields: [
        { key: 'name', label: 'Node Name', type: 'text', placeholder: node.name, required: true },
        { key: 'ipAddress', label: 'IP Address', type: 'text', placeholder: node.ipAddress, required: true },
        { key: 'maxCameras', label: 'Max Cameras', type: 'number', placeholder: String(node.maxCameras) },
      ],
      onSubmit: (data) => this.edgeNodeService.updateEdgeNode(node.id, data as never),
      onSuccess: () => { this.nodes$ = this.edgeNodeService.getEdgeNodes(); },
    });
  }

  deleteNode(node: IEdgeNode): void {
    if (!confirm(`Delete edge node "${node.name}"? This cannot be undone.`)) return;
    this.edgeNodeService.deleteEdgeNode(node.id).subscribe({
      next: () => {
        this.toastr.success('Edge node deleted');
        this.nodes$ = this.edgeNodeService.getEdgeNodes();
      },
    });
  }
}
