import { IsNotEmpty, IsOptional, IsString } from 'class-validator';

export class CreateZoneAssignmentDto {
  @IsString()
  @IsNotEmpty()
  authUserId!: string;

  @IsString()
  @IsNotEmpty()
  zoneId!: string;

  @IsOptional()
  @IsString()
  notes?: string;
}