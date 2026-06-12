import {
  Body,
  Controller,
  Delete,
  Get,
  Param,
  Patch,
  Post,
  UseGuards,
} from '@nestjs/common';

import { EdgeNodesService } from './edge-nodes.service';
import { CreateEdgeNodeDto } from './dto/create-edge-node.dto';
import { UpdateEdgeNodeDto } from './dto/update-edge-node.dto';
import { JwtAuthGuard } from '../../../../../libs/common/src/guards/jwt-auth.guard';
import { RolesGuard } from '../../../../../libs/common/src/guards/roles.guards';
import { Roles } from '../../../../../libs/common/src/decorators/roles.decorator';
import { UserRole } from '../../../../../libs/common/enums/user.role.enum';

@Controller('edge-nodes')
@UseGuards(JwtAuthGuard) // ✅ All endpoints require valid JWT
export class EdgeNodesController {
  constructor(private readonly edgeNodesService: EdgeNodesService) {}

  // ─── Create ────────────────────────────────────────────────────────────────
  // ✅ Admin only — edge nodes are infrastructure
  @Post()
  @UseGuards(RolesGuard)
  @Roles(UserRole.ADMIN)
  create(@Body() dto: CreateEdgeNodeDto) {
    return this.edgeNodesService.create(dto);
  }

  // ─── Read All ──────────────────────────────────────────────────────────────
  // ✅ Admin + supervisor can view edge nodes
  @Get()
  @UseGuards(RolesGuard)
  @Roles(UserRole.ADMIN, UserRole.SUPERVISOR)
  findAll() {
    return this.edgeNodesService.findAll();
  }


  @Get('by-code/:code')
  @UseGuards(RolesGuard)
  @Roles(UserRole.ADMIN, UserRole.SUPERVISOR, UserRole.EDGE_SERVICE, UserRole.INCIDENT_SERVICE)
  findByCode(@Param('code') code: string) {
    return this.edgeNodesService.findByCode(code);
  }
  // ─── Read One ──────────────────────────────────────────────────────────────
  @Get(':id')
  @UseGuards(RolesGuard)
  @Roles(UserRole.ADMIN, UserRole.SUPERVISOR)
  findOne(@Param('id') id: string) {
    return this.edgeNodesService.findOne(id);
  }

  // ─── Update ────────────────────────────────────────────────────────────────
  // ✅ Admin only
  @Patch(':id')
  @UseGuards(RolesGuard)
  @Roles(UserRole.ADMIN)
  update(@Param('id') id: string, @Body() dto: UpdateEdgeNodeDto) {
    return this.edgeNodesService.update(id, dto);
  }

  // ─── Delete ────────────────────────────────────────────────────────────────
  // ✅ Admin only
  @Delete(':id')
  @UseGuards(RolesGuard)
  @Roles(UserRole.ADMIN)
  remove(@Param('id') id: string) {
    return this.edgeNodesService.remove(id);
  }
}
