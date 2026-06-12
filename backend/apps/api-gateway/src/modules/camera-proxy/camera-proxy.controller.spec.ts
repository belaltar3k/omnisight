import { Test, TestingModule } from '@nestjs/testing';
import { CameraProxyController } from './camera-proxy.controller';

describe('CameraProxyController', () => {
  let controller: CameraProxyController;

  beforeEach(async () => {
    const module: TestingModule = await Test.createTestingModule({
      controllers: [CameraProxyController],
    }).compile();

    controller = module.get<CameraProxyController>(CameraProxyController);
  });

  it('should be defined', () => {
    expect(controller).toBeDefined();
  });
});
