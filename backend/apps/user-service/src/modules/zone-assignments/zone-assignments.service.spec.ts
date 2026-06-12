import { Test, TestingModule } from '@nestjs/testing';
import { ZoneAssignmentsService } from './zone-assignments.service';

describe('ZoneAssignmentsService', () => {
  let service: ZoneAssignmentsService;

  beforeEach(async () => {
    const module: TestingModule = await Test.createTestingModule({
      providers: [ZoneAssignmentsService],
    }).compile();

    service = module.get<ZoneAssignmentsService>(ZoneAssignmentsService);
  });

  it('should be defined', () => {
    expect(service).toBeDefined();
  });
});
