const EXPECTED_NODE_VERSION = '22.23.1';
const EXPECTED_NPM_VERSION = '10.9.8';

const npmUserAgent = process.env.npm_config_user_agent ?? '';
const npmVersionMatch = npmUserAgent.match(/(?:^|\s)npm\/([^\s]+)/);
const actualNodeVersion = process.versions.node;
const actualNpmVersion = npmVersionMatch?.[1] ?? null;

const errors = [];

if (actualNodeVersion !== EXPECTED_NODE_VERSION) {
  errors.push(
    `Node ${EXPECTED_NODE_VERSION} is required; found ${actualNodeVersion}.`
  );
}

if (actualNpmVersion !== EXPECTED_NPM_VERSION) {
  const found = actualNpmVersion ?? 'an unknown npm version';
  errors.push(
    `npm ${EXPECTED_NPM_VERSION} is required; found ${found}. Run this check through npm.`
  );
}

if (errors.length > 0) {
  for (const error of errors) {
    console.error(`[release-runtime] ${error}`);
  }
  process.exitCode = 1;
} else {
  console.log(
    `[release-runtime] Node ${actualNodeVersion} and npm ${actualNpmVersion} verified.`
  );
}
