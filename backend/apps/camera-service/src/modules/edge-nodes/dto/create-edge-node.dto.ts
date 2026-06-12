import { IsEnum, IsNotEmpty, IsNumber, IsOptional, IsString, Min } from 'class-validator';
import { EdgeNodeStatus } from '../../../../../../libs/common/enums/edge-node-status.enum';

export class CreateEdgeNodeDto {
  @IsString()
  @IsNotEmpty()
  name!: string;

  @IsString()
  @IsNotEmpty()
  code!: string;

  @IsString()
  @IsNotEmpty()
  ipAddress!: string;

  @IsOptional()
  @IsEnum(EdgeNodeStatus)
  status?: EdgeNodeStatus;

  @IsOptional()
  @IsNumber()
  @Min(1)
  maxCameras?: number;
}