import { IsEnum, IsNotEmpty, IsNumber, IsString, Max, Min } from 'class-validator';
import { CrimeType } from '../../entities/incident.entity';

export class EdgeClassifyDto {
  @IsString()
  @IsNotEmpty()
  trackId!: string;

  @IsEnum(CrimeType, { message: `crimeType must be one of: ${Object.values(CrimeType).join(', ')}` })
  crimeType!: CrimeType;

  @IsNumber()
  @Min(0)
  @Max(1)
  confidence!: number;
}
