import { IsBoolean, IsEnum, IsIn, IsNumber, IsOptional, IsString, Min } from 'class-validator';
import { Transform, Type } from 'class-transformer';
import { CrimeType, IncidentPriority, IncidentStatus } from '../../entities/incident.entity';

const SORTABLE_FIELDS = [
  'detectedAt', 'createdAt', 'updatedAt',
  'priority', 'status', 'confidence', 'crimeType',
  'assignedAt', 'resolvedAt',
] as const;

export class FilterIncidentsDto {
  @IsOptional()
  @IsEnum(CrimeType)
  crimeType?: CrimeType;

  @IsOptional()
  @IsEnum(IncidentStatus)
  status?: IncidentStatus;

  @IsOptional()
  @IsEnum(IncidentPriority)
  priority?: IncidentPriority;

  @IsOptional()
  @IsString()
  zoneId?: string;

  @IsOptional()
  @IsString()
  cameraId?: string;

  @IsOptional()
  @IsString()
  assignedTo?: string;

  @IsOptional()
  @IsString()
  dateFrom?: string;

  @IsOptional()
  @IsString()
  dateTo?: string;

  @IsOptional()
  @Type(() => Number)
  @IsNumber()
  minConfidence?: number;

  @IsOptional()
  @Transform(({ value }) => value === 'true')
  @IsBoolean()
  isFalsePositive?: boolean;

  @IsOptional()
  @Type(() => Number)
  @IsNumber()
  @Min(1)
  page?: number = 1;

  @IsOptional()
  @Type(() => Number)
  @IsNumber()
  @Min(1)
  limit?: number = 20;

  @IsOptional()
  @IsIn(SORTABLE_FIELDS, { message: `sortBy must be one of: ${SORTABLE_FIELDS.join(', ')}` })
  sortBy?: string = 'detectedAt';

  @IsOptional()
  @IsIn(['asc', 'desc'], { message: 'sortOrder must be asc or desc' })
  sortOrder?: 'asc' | 'desc' = 'desc';
}
