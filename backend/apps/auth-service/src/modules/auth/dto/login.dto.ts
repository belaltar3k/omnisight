import { IsEmail, IsOptional, IsString, ValidateIf } from 'class-validator';

export class LoginDto {
  // Either email or employeeCode must be provided.
  @ValidateIf((o) => !o.employeeCode)
  @IsEmail()
  email?: string;

  @ValidateIf((o) => !o.email)
  @IsString()
  employeeCode?: string;

  @IsString()
  password!: string;
}
