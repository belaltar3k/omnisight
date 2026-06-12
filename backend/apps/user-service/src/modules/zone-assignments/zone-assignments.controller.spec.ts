import { Test, TestingModule } from '@nestjs/testing';
import { ZoneAssignmentsController } from './zone-assignments.controller';

describe('ZoneAssignmentsController', () => {
  let controller: ZoneAssignmentsController;

  beforeEach(async () => {
    const module: TestingModule = await Test.createTestingModule({
      controllers: [ZoneAssignmentsController],
    }).compile();

    controller = module.get<ZoneAssignmentsController>(ZoneAssignmentsController);
  });

  it('should be defined', () => {
    expect(controller).toBeDefined();
  });
});
