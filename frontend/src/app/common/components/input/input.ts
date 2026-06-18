import { Component, computed, forwardRef, input, signal } from "@angular/core";
import { ControlValueAccessor, NG_VALUE_ACCESSOR } from "@angular/forms";

@Component({
  selector: "app-input",
  imports: [],
  templateUrl: "./input.html",
  styleUrl: "./input.css",
  standalone: true,
  providers: [
    {
      provide: NG_VALUE_ACCESSOR,
      useExisting: forwardRef(() => InputComponent),
      multi: true,
    },
  ],
})
export class InputComponent implements ControlValueAccessor {
  readonly label = input<string>();
  readonly type = input("text");
  readonly id = input.required<string>();
  readonly placeholder = input("");
  readonly name = input("");
  readonly autocomplete = input("");
  readonly element = input<"input" | "textarea">("input");
  readonly required = input(false);

  protected readonly value = signal("");
  protected readonly isDisabled = signal(false);
  protected readonly showPassword = signal(false);

  protected readonly isPassword = computed(
    () =>
      this.type() === "password" ||
      this.id().toLowerCase().includes("password"),
  );

  protected readonly currentType = computed(() =>
    this.isPassword() && this.showPassword() ? "text" : this.type(),
  );

  private readonly cva = {
    onChange: (_: string) => {},
    onTouched: () => {},
  };

  writeValue(value: string | null): void {
    this.value.set(value ?? "");
  }

  registerOnChange(fn: (v: string) => void): void {
    this.cva.onChange = fn;
  }

  registerOnTouched(fn: () => void): void {
    this.cva.onTouched = fn;
  }

  setDisabledState(isDisabled: boolean): void {
    this.isDisabled.set(isDisabled);
  }

  protected onInput(event: Event): void {
    const val = (event.target as HTMLInputElement | HTMLTextAreaElement).value;
    this.value.set(val);
    this.cva.onChange(val);
  }

  protected onBlur(): void {
    this.cva.onTouched();
  }
}
