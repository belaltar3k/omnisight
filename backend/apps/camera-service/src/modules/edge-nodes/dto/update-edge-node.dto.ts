import { PartialType } from '@nestjs/mapped-types';
import { CreateEdgeNodeDto } from './create-edge-node.dto';

export class UpdateEdgeNodeDto extends PartialType(CreateEdgeNodeDto) {}