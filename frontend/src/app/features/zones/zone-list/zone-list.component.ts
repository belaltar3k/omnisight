import { Component, inject } from "@angular/core";
import { ZoneService } from "@core/services";
import { ModalService } from "@core/services/modal.service";
import { ButtonComponent } from "@common/components/button/button.component";
import { AsyncPipe } from "@angular/common";
import { BtnStylesEnum } from "@shared/enums";
import { IZone } from "@shared/interfaces/zone";
import { ToastrService } from "ngx-toastr";

@Component({
    selector: "app-zone-list",
    standalone: true,
    templateUrl: "./zone-list.component.html",
    imports: [ButtonComponent, AsyncPipe],
})
export class ZoneListComponent {
    private readonly zoneService = inject(ZoneService);
    private readonly modalService = inject(ModalService);
    private readonly toastr = inject(ToastrService);

    zones$ = this.zoneService.getZones();
    protected readonly BtnStylesEnum = BtnStylesEnum;

    openAddZoneModal(): void {
        this.modalService.open({
            title: 'Add Zone',
            submitLabel: 'Add Zone',
            fields: [
                { key: 'name', label: 'Zone Name', type: 'text', placeholder: 'Enter zone name', required: true },
                { key: 'description', label: 'Description', type: 'textarea', placeholder: 'Enter a description (optional)' },
            ],
            onSubmit: (data) => this.zoneService.createZone(data as never),
            onSuccess: () => { this.zones$ = this.zoneService.getZones(); },
        });
    }

    openEditZoneModal(zone: IZone): void {
        this.modalService.open({
            title: 'Edit Zone',
            submitLabel: 'Save Changes',
            fields: [
                { key: 'name', label: 'Zone Name', type: 'text', placeholder: zone.name, required: true },
                { key: 'description', label: 'Description', type: 'textarea', placeholder: zone.description ?? '' },
            ],
            onSubmit: (data) => this.zoneService.updateZone(zone.id, data as never),
            onSuccess: () => { this.zones$ = this.zoneService.getZones(); },
        });
    }

    deleteZone(zone: IZone): void {
        if (!confirm(`Delete zone "${zone.name}"? This will fail if cameras are still assigned.`)) return;
        this.zoneService.deleteZone(zone.id).subscribe({
            next: () => {
                this.toastr.success('Zone deleted');
                this.zones$ = this.zoneService.getZones();
            },
        });
    }
}