function configureRuntimeEnv({ appIsPackaged, apiBaseUrl, env = process.env } = {}) {
  const targetEnv = env && typeof env === 'object' ? env : process.env;
  targetEnv.APP_IS_PACKAGED = appIsPackaged ? '1' : '0';

  if (appIsPackaged) {
    delete targetEnv.LICENSE_BYPASS;
    delete targetEnv.ALLOW_DEV_LICENSE_BYPASS;
    return targetEnv;
  }

  if (apiBaseUrl) {
    targetEnv.API_BASE_URL = String(apiBaseUrl);
  }
  targetEnv.ALLOW_DEV_LICENSE_BYPASS = '1';
  if (!targetEnv.VOX_STELLA_ENV) {
    targetEnv.VOX_STELLA_ENV = 'development';
  }
  if (!targetEnv.FLASK_ENV) {
    targetEnv.FLASK_ENV = 'development';
  }
  return targetEnv;
}

module.exports = {
  configureRuntimeEnv,
};
