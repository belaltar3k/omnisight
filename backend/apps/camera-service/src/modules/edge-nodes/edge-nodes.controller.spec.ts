import { Test, TestingModule } from '@nestjs/testing';
import { EdgeNodesController } from './edge-nodes.controller';

describe('EdgeNodesController', () => {
  let controller: EdgeNodesController;

  beforeEach(async () => {
    const module: TestingModule = await Test.createTestingModule({
      controllers: [EdgeNodesController],
    }).compile();

    controller = module.get<EdgeNodesController>(EdgeNodesController);
  });

  it('should be defined', () => {
    expect(controller).toBeDefined();
  });
});
