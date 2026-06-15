import { IAlertPreferences } from './alert.interface';

export interface IUpdatePreferencesRequest
  extends Omit<IAlertPreferences, 'userId'> {}
