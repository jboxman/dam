const fs = require('fs');
const path = require('path');

const defaultUser = process.env['USER'];
const defaultUserDir = process.env['HOME'];
const configDir = path.join(defaultUserDir, '.dam');
const configFile = path.join(configDir, 'config.json');
const exiftoolConfigFile = path.join(configDir, 'exiftool.conf');

function loadConfig() {
  let config;

  const defaultConfig = {
    defaultUser,
    stagingDir: path.join(defaultUserDir, `Self/repos/photos/photographers`),
    digikamDir: path.join(defaultUserDir, `Self/repos/photos-dk/photographers`),
    photographers: {
      [defaultUser]: {
        copyrightArgs: path.join(configDir, `${defaultUser}-copyright.conf`)
      }
    }
  };

  try {
    config = JSON.parse(fs.readFileSync(configFile));
  }
  catch(e) {
    config = {};
  }

  config = Object.assign(defaultConfig, config);

  return config;
}

function prepareConfig() {
  if(! fs.existsSync(configDir))
    fs.mkdirSync(configDir);

  if(! fs.existsSync(exiftoolConfigFile))
    fs.copyFileSync(
      path.join(__dirname, 'config/exiftool.conf'), path.join(configDir, 'exiftool.conf'));
}

module.exports = {
  loadConfig,
  prepareConfig,
  exiftoolConfigFile,
};
