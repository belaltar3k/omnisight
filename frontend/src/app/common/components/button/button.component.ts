import {Component, computed, input, InputSignal} from '@angular/core';
import {BtnStylesEnum} from "@shared/enums";

@Component({
    selector: 'app-button',
    imports: [],
    templateUrl: './button.component.html',
})
export class ButtonComponent {
    message: InputSignal<string> = input('Add Zone')
    icon: InputSignal<string> = input('plus')
    disabled: InputSignal<boolean> = input(false)
    type: InputSignal<'button' | 'submit' | 'reset'> = input<'button' | 'submit' | 'reset'>('submit')
    btnStyle: InputSignal<BtnStylesEnum> = input<BtnStylesEnum>(BtnStylesEnum.BTN_BlACK)

    protected readonly iconClass = computed(() => {
        const icon = this.icon();
        return icon.startsWith('fa-') ? `fas ${icon}` : `fas fa-${icon}`;
    });
    protected readonly BtnStylesEnum = BtnStylesEnum;
}