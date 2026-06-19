import {
  Body,
  Controller,
  Delete,
  Get,
  Headers,
  HttpCode,
  HttpStatus,
  Param,
  Patch,
  Post,
  Query,
  Req,
  UseGuards,
} from '@nestjs/common';

import { IncidentsService } from './incidents.service';
import { EdgeSyncDto } from './dto/edge-sync.dto';
import { EdgeClassifyDto } from './dto/edge-classify.dto';
import { CreateIncidentDto } from './dto/create-incident.dto';
import { UpdateIncidentDto } from './dto/update-incident.dto';
import { AssignIncidentDto } from './dto/assign-incident.dto';
import { ResolveIncidentDto } from './dto/resolve-incident.dto';
import { FalsePositiveDto } from './dto/false-positive.dto';
import { AddNoteDto } from './dto/add-note.dto';
import { FilterIncidentsDto } from './dto/filter-incidents.dto';
import { JwtAuthGuard } from '../../../../../libs/common/src/guards/jwt-auth.guard';
import { RolesGuard } from '../../../../../libs/common/src/guards/roles.guards';
import { Roles } from '../../../../../libs/common/src/decorators/roles.decorator'
import { UserRole } from '../../../../../libs/common/enums/user.role.enum';

@Controller()
export class IncidentsController {
  constructor(private readonly incidentsService: IncidentsService) {}

  // ══════════════════════════════════════════════════════════════════════════
  // EDGE ENDPOINTS — no JWT, protected by shared secret
  // ══════════════════════════════════════════════════════════════════════════

  // Step 1: edge node sends abnormal detection
  @Post('edge/sync')
  @HttpCode(HttpStatus.OK)
  async edgeSync(
    @Body() dto: EdgeSyncDto,
    @Headers('x-edge-secret') secret: string,
  ) {
    this.incidentsService.verifyEdgeSecret(secret);
    return this.incidentsService.syncFromEdge(dto);
  }

  // Step 2: edge node sends crime classification
  @Post('edge/classify')
  @HttpCode(HttpStatus.OK)
  async edgeClassify(
    @Body() dto: EdgeClassifyDto,
    @Headers('x-edge-secret') secret: string,
  ) {
    this.incidentsService.verifyEdgeSecret(secret);
    return this.incidentsService.classifyFromEdge(dto);
  }

  // ══════════════════════════════════════════════════════════════════════════
  // INTERNAL — service-to-service, protected by edge secret (no JWT)
  // ══════════════════════════════════════════════════════════════════════════

  @Get('internal/incidents')
  @HttpCode(HttpStatus.OK)
  async internalFindAll(
    @Query() filters: FilterIncidentsDto,
    @Headers('x-edge-secret') secret: string,
  ) {
    this.incidentsService.verifyEdgeSecret(secret);
    return this.incidentsService.findAll(filters);
  }

  // ══════════════════════════════════════════════════════════════════════════
  // CRUD — JWT protected
  // ══════════════════════════════════════════════════════════════════════════

  @Post('incidents')
  @UseGuards(JwtAuthGuard, RolesGuard)
  @Roles(UserRole.ADMIN, UserRole.SUPERVISOR)
  create(@Body() dto: CreateIncidentDto, @Req() req: any) {
    return this.incidentsService.create(dto, req.user.sub);
  }

  @Get('incidents')
  @UseGuards(JwtAuthGuard, RolesGuard)
  @Roles(UserRole.ADMIN, UserRole.SUPERVISOR)
  findAll(@Query() filters: FilterIncidentsDto) {
    return this.incidentsService.findAll(filters);
  }

  // ✅ IMPORTANT: specific routes before /:id
  @Get('incidents/my')
  @UseGuards(JwtAuthGuard)
  findMyIncidents(@Req() req: any, @Query() filters: FilterIncidentsDto) {
    filters.assignedTo = req.user.sub;
    return this.incidentsService.findAll(filters);
  }

  @Get('incidents/:id')
  @UseGuards(JwtAuthGuard)
  findOne(@Param('id') id: string) {
    return this.incidentsService.findOne(id);
  }

  @Patch('incidents/:id')
  @UseGuards(JwtAuthGuard, RolesGuard)
  @Roles(UserRole.ADMIN, UserRole.SUPERVISOR)
  update(
    @Param('id') id: string,
    @Body() dto: UpdateIncidentDto,
    @Req() req: any,
  ) {
    return this.incidentsService.update(id, dto, req.user.sub);
  }

  @Delete('incidents/:id')
  @UseGuards(JwtAuthGuard, RolesGuard)
  @Roles(UserRole.ADMIN)
  remove(@Param('id') id: string, @Req() req: any) {
    return this.incidentsService.remove(id, req.user.sub);
  }

  // ══════════════════════════════════════════════════════════════════════════
  // ACTIONS
  // ══════════════════════════════════════════════════════════════════════════

  @Post('incidents/:id/assign')
  @HttpCode(HttpStatus.OK)
  @UseGuards(JwtAuthGuard, RolesGuard)
  @Roles(UserRole.ADMIN, UserRole.SUPERVISOR)
  assign(
    @Param('id') id: string,
    @Body() dto: AssignIncidentDto,
    @Req() req: any,
  ) {
    return this.incidentsService.assign(id, dto, req.user.sub);
  }

  @Post('incidents/:id/acknowledge')
  @HttpCode(HttpStatus.OK)
  @UseGuards(JwtAuthGuard)
  acknowledge(@Param('id') id: string, @Req() req: any) {
    return this.incidentsService.acknowledge(id, req.user.sub);
  }

  @Post('incidents/:id/investigate')
  @HttpCode(HttpStatus.OK)
  @UseGuards(JwtAuthGuard)
  investigate(@Param('id') id: string, @Req() req: any) {
    return this.incidentsService.investigate(id, req.user.sub);
  }

  @Post('incidents/:id/dispatch')
  @HttpCode(HttpStatus.OK)
  @UseGuards(JwtAuthGuard, RolesGuard)
  @Roles(UserRole.ADMIN, UserRole.SUPERVISOR)
  dispatch(@Param('id') id: string, @Req() req: any) {
    return this.incidentsService.dispatch(id, req.user.sub);
  }

  @Post('incidents/:id/on-scene')
  @HttpCode(HttpStatus.OK)
  @UseGuards(JwtAuthGuard)
  onScene(@Param('id') id: string, @Req() req: any) {
    return this.incidentsService.onScene(id, req.user.sub);
  }

  @Post('incidents/:id/resolve')
  @HttpCode(HttpStatus.OK)
  @UseGuards(JwtAuthGuard)
  resolve(
    @Param('id') id: string,
    @Body() dto: ResolveIncidentDto,
    @Req() req: any,
  ) {
    return this.incidentsService.resolve(id, dto, req.user.sub);
  }

  @Post('incidents/:id/false-positive')
  @HttpCode(HttpStatus.OK)
  @UseGuards(JwtAuthGuard, RolesGuard)
  @Roles(UserRole.ADMIN, UserRole.SUPERVISOR)
  falsePositive(
    @Param('id') id: string,
    @Body() dto: FalsePositiveDto,
    @Req() req: any,
  ) {
    return this.incidentsService.markFalsePositive(id, dto, req.user.sub);
  }

  // ══════════════════════════════════════════════════════════════════════════
  // NOTES & TIMELINE
  // ══════════════════════════════════════════════════════════════════════════

  @Post('incidents/:id/notes')
  @HttpCode(HttpStatus.OK)
  @UseGuards(JwtAuthGuard)
  addNote(
    @Param('id') id: string,
    @Body() dto: AddNoteDto,
    @Req() req: any,
  ) {
    return this.incidentsService.addNote(id, dto, req.user.sub);
  }

  @Get('incidents/:id/notes')
  @UseGuards(JwtAuthGuard)
  getNotes(@Param('id') id: string) {
    return this.incidentsService.getNotes(id);
  }

  @Get('incidents/:id/timeline')
  @UseGuards(JwtAuthGuard)
  getTimeline(@Param('id') id: string) {
    return this.incidentsService.getTimeline(id);
  }
}
