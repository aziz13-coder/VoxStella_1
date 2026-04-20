const { configureRuntimeEnv } = require('../main/runtime-env');

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

{
  const env = {};
  configureRuntimeEnv({ appIsPackaged: false, apiBaseUrl: 'http://127.0.0.1:52525', env });
  assert(env.APP_IS_PACKAGED === '0', 'dev runtime should mark APP_IS_PACKAGED=0');
  assert(env.API_BASE_URL === 'http://127.0.0.1:52525', 'dev runtime should expose the API base URL');
  assert(env.ALLOW_DEV_LICENSE_BYPASS === '1', 'dev runtime should enable the dev license bypass');
  assert(env.VOX_STELLA_ENV === 'development', 'dev runtime should mark VOX_STELLA_ENV=development');
  assert(env.FLASK_ENV === 'development', 'dev runtime should mark FLASK_ENV=development');
}

{
  const env = {
    LICENSE_BYPASS: '1',
    ALLOW_DEV_LICENSE_BYPASS: '1',
    FLASK_ENV: 'production',
  };
  configureRuntimeEnv({ appIsPackaged: true, apiBaseUrl: 'http://127.0.0.1:52525', env });
  assert(env.APP_IS_PACKAGED === '1', 'packaged runtime should mark APP_IS_PACKAGED=1');
  assert(!('LICENSE_BYPASS' in env), 'packaged runtime should clear LICENSE_BYPASS');
  assert(!('ALLOW_DEV_LICENSE_BYPASS' in env), 'packaged runtime should clear ALLOW_DEV_LICENSE_BYPASS');
  assert(env.FLASK_ENV === 'production', 'packaged runtime should not rewrite unrelated env vars');
}

console.log('runtimeEnv tests passed');
