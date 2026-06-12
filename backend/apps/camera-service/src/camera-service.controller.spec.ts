import { Test, TestingModule } from '@nestjs/testing';
import { CameraServiceController } from './camera-service.controller';
import { CameraServiceService } from './camera-service.service';

describe('CameraServiceController', () => {
  let cameraServiceController: CameraServiceController;

  beforeEach(async () => {
    const app: TestingModule = await Test.createTestingModule({
      controllers: [CameraServiceController],
      providers: [CameraServiceService],
    }).compile();

    cameraServiceController = app.get<CameraServiceController>(CameraServiceController);
  });

  describe('root', () => {
    it('should return "Hello World!"', () => {
      expect(cameraServiceController.getHello()).toBe('Hello World!');
    });
  });
});
