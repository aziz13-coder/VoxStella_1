import { describe, expect, it } from 'vitest';

import {
  getHorarySubmitDisabledReason,
  HORARY_API_OFFLINE_MESSAGE,
  HORARY_ACTIVATION_REQUIRED_MESSAGE,
  requiresHoraryActivation,
} from '../utils/licenseFlow.mjs';

describe('licenseFlow', () => {
  it('requires activation only for packaged unlicensed runtime', () => {
    expect(
      requiresHoraryActivation({
        packagedRuntime: true,
        devLicenseRuntime: false,
        licenseActive: false,
      }),
    ).toBe(true);

    expect(
      requiresHoraryActivation({
        packagedRuntime: true,
        devLicenseRuntime: false,
        licenseActive: true,
      }),
    ).toBe(false);

    expect(
      requiresHoraryActivation({
        packagedRuntime: true,
        devLicenseRuntime: true,
        licenseActive: false,
      }),
    ).toBe(false);
  });

  it('surfaces activation before field-level validation', () => {
    expect(
      getHorarySubmitDisabledReason({
        requiresActivation: true,
        question: '',
        location: '',
      }),
    ).toBe(HORARY_ACTIVATION_REQUIRED_MESSAGE);
  });

  it('preserves existing field validation when activation is not required', () => {
    expect(
      getHorarySubmitDisabledReason({
        question: '',
        location: 'London, UK',
      }),
    ).toBe('Enter your question first.');

    expect(
      getHorarySubmitDisabledReason({
        question: 'Will I get the job?',
        location: '',
      }),
    ).toBe('Enter a location first.');

    expect(
      getHorarySubmitDisabledReason({
        question: 'Will I get the job?',
        location: 'London, UK',
      }),
    ).toBe('');
  });

  it('blocks chart casting while the horary API is offline', () => {
    expect(
      getHorarySubmitDisabledReason({
        question: 'Will I get the job?',
        location: 'London, UK',
        apiStatus: 'offline',
      }),
    ).toBe(HORARY_API_OFFLINE_MESSAGE);
  });
});
