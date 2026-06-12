import { Test, TestingModule } from '@nestjs/testing';
import { UserProxyController } from './user-proxy.controller';

describe('UserProxyController', () => {
  let controller: UserProxyController;

  beforeEach(async () => {
    const module: TestingModule = await Test.createTestingModule({
      controllers: [UserProxyController],
    }).compile();

    controller = module.get<UserProxyController>(UserProxyController);
  });

  it('should be defined', () => {
    expect(controller).toBeDefined();
  });
});
