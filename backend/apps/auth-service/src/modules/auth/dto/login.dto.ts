import { IsString } from 'class-validator';

export class LoginDto {
  // Accepts either an email or an employee code.
  @IsString()
  identifier!: string;

  @IsString()
  password!: string;
}
