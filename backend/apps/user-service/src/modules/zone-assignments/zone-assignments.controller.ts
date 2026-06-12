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

import { ZoneAssignmentsService } from './zone-assignments.service';
import { CreateZoneAssignmentDto } from './dto/create-zone-assignment.dto';
import { ReassignZoneDto } from './dto/reassign-zone.dto';
import { JwtAuthGuard } from '../../../../../libs/common/src/guards/jwt-auth.guard';
import { RolesGuard } from '../../../../../libs/common/src/guards/roles.guards';
import { Roles } from '../../../../../libs/common/src/decorators/roles.decorator';
import { UserRole } from '../../../../../libs/common/enums/user.role.enum';

@Controller('zone-assignments')
@UseGuards(JwtAuthGuard) // ✅ All endpoints require a valid JWT
export class ZoneAssignmentsController {
  constructor(
    private readonly zoneAssignmentsService: ZoneAssignmentsService,
  ) {}

  // ─── Create ────────────────────────────────────────────────────────────────
  // ✅ Only admin/supervisor can assign users to zones
  @Post()
  @UseGuards(RolesGuard)
  @Roles(UserRole.ADMIN, UserRole.SUPERVISOR)
  create(@Body() dto: CreateZoneAssignmentDto) {
    return this.zoneAssignmentsService.create(dto);
  }

  // ─── List All ──────────────────────────────────────────────────────────────
  // ✅ Admin only — full list of all assignments in the system
  @Get()
  @UseGuards(RolesGuard)
  @Roles(UserRole.ADMIN)
  findAll() {
    return this.zoneAssignmentsService.findAll();
  }

  // ─── Users in a Zone (with profiles) ──────────────────────────────────────
  // ✅ IMPORTANT: stays ABOVE /zone/:zoneId to avoid route conflict
  // ✅ Admin + supervisor can see who is in a zone
  @Get('zone/:zoneId/users')
  @UseGuards(RolesGuard)
  @Roles(UserRole.ADMIN, UserRole.SUPERVISOR, UserRole.ALERT_SERVICE)
  findUsersByZone(@Param('zoneId') zoneId: string) {
    return this.zoneAssignmentsService.findUsersByZone(zoneId);
  }

  // ─── Assignments by Zone ───────────────────────────────────────────────────
  @Get('zone/:zoneId')
  @UseGuards(RolesGuard)
  @Roles(UserRole.ADMIN, UserRole.SUPERVISOR)
  findByZone(@Param('zoneId') zoneId: string) {
    return this.zoneAssignmentsService.findByZone(zoneId);
  }

  // ─── Assignments by User ───────────────────────────────────────────────────
  // ✅ Admin/supervisor can query any user; guards in service layer if needed
  @Get('user/:authUserId')
  @UseGuards(RolesGuard)
  @Roles(UserRole.ADMIN, UserRole.SUPERVISOR)
  findByUser(@Param('authUserId') authUserId: string) {
    return this.zoneAssignmentsService.findByUser(authUserId);
  }

  // ─── Reassign to New Zone ──────────────────────────────────────────────────
  // ✅ Only admin/supervisor can reassign
  @Patch(':id/reassign')
  @UseGuards(RolesGuard)
  @Roles(UserRole.ADMIN, UserRole.SUPERVISOR)
  reassign(@Param('id') id: string, @Body() dto: ReassignZoneDto) {
    return this.zoneAssignmentsService.reassign(id, dto);
  }

  // ─── Delete by User + Zone ─────────────────────────────────────────────────
  // ✅ IMPORTANT: stays ABOVE /:id to avoid route conflict
  // ✅ Only admin/supervisor can remove assignments
  @Delete('user/:authUserId/zone/:zoneId')
  @UseGuards(RolesGuard)
  @Roles(UserRole.ADMIN, UserRole.SUPERVISOR)
  removeByUserAndZone(
    @Param('authUserId') authUserId: string,
    @Param('zoneId') zoneId: string,
  ) {
    return this.zoneAssignmentsService.removeByUserAndZone(authUserId, zoneId);
  }

  // ─── Delete by ID ──────────────────────────────────────────────────────────
  @Delete(':id')
  @UseGuards(RolesGuard)
  @Roles(UserRole.ADMIN, UserRole.SUPERVISOR)
  remove(@Param('id') id: string) {
    return this.zoneAssignmentsService.remove(id);
  }
}
