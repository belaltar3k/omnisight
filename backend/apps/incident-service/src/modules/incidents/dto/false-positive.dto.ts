import { IsNotEmpty, IsString } from 'class-validator';

export class FalsePositiveDto {
  @IsString()
  @IsNotEmpty()
  reason!: string;
}
