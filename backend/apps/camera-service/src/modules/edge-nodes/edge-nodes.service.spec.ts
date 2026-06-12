import { Test, TestingModule } from '@nestjs/testing';
import { EdgeNodesService } from './edge-nodes.service';

describe('EdgeNodesService', () => {
  let service: EdgeNodesService;

  beforeEach(async () => {
    const module: TestingModule = await Test.createTestingModule({
      providers: [EdgeNodesService],
    }).compile();

    service = module.get<EdgeNodesService>(EdgeNodesService);
  });

  it('should be defined', () => {
    expect(service).toBeDefined();
  });
});
