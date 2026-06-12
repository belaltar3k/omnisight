import { IsDateString, IsEnum, IsNotEmpty, IsNumber, IsOptional, IsString, Max, Min } from 'class-validator';
import { CrimeType } from '../../entities/incident.entity';

export class CreateIncidentDto {
  @IsString()
  @IsNotEmpty()
  cameraId!: string;

  @IsString()
  @IsNotEmpty()
  cameraCode!: string;

  @IsString()
  @IsNotEmpty()
  zoneId!: string;

  @IsString()
  @IsNotEmpty()
  edgeNodeId!: string;

  @IsEnum(CrimeType)
  crimeType!: CrimeType;

  @IsNumber()
  @Min(0)
  @Max(1)
  confidence!: number;

  @IsDateString()
  detectedAt!: string;

  @IsOptional()
  @IsString()
  videoUrl?: string;

  @IsOptional()
  @IsString()
  thumbnailUrl?: string;
}
