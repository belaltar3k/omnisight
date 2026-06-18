import { Observable } from 'rxjs';

export type ModalFieldType = 'text' | 'email' | 'password' | 'number' | 'textarea' | 'select';

export interface IModalSelectOption {
  label: string;
  value: string;
}

export interface IModalField {
  key: string;
  label: string;
  type: ModalFieldType;
  placeholder?: string;
  required?: boolean;
  options?: IModalSelectOption[];
}

export interface IModalConfig {
  title: string;
  submitLabel?: string;
  fields: IModalField[];
  onSubmit: (data: Record<string, unknown>) => Observable<unknown>;
  onSuccess?: () => void;
}
