import { IsOptional, IsString, MinLength } from 'class-validator';

export class CreateZoneDto {
  @IsString()
  @MinLength(2)
  name!: string;

  @IsOptional()
  @IsString()
  description?: string;

  @IsOptional()
  @IsString()
  location?: string;
}