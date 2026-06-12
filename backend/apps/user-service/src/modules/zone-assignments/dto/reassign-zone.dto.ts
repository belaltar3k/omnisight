import { IsNotEmpty, IsString } from 'class-validator';

export class ReassignZoneDto {
  @IsString()
  @IsNotEmpty()
  newZoneId!: string;
}