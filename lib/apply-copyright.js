const path = require('path');
const fs = require('fs');

const {
  runLog,
  touch,
  findWithExiftool
} = require('.');

const { loadConfig } = require('./config');

const config = loadConfig();

// TODO -
// This needs to pull from ~/.dam
// This needs to look for an --owner <name> file there

async function action(photoDir, { dry } = cmd) {
  const argsFile = config.photographers[config.defaultUser].copyrightArgs;

  if(! fs.existsSync(argsFile)) {
    console.error(`Cannot open exiftool args file: ${argsFile}`);
    process.exit(1);
  }

  if(! fs.existsSync(photoDir)) {
    console.error(`Directory does not exist: ${photoDir}`);
    process.exit(1);
  }

  const output = await findWithExiftool({
    dry,
    path: photoDir,
    fileTypes: ['jpg', 'nef', 'heic', 'mov'],
    extraArgs: `-@ ${config.photographers[config.defaultUser].copyrightArgs}`
  });

  // [ '    1 directories scanned', '  226 image files updated' ]
  if(! dry) {
    output.map(v => v.trim())
      .forEach(line => {
        runLog(line);
      });

    if(output.some(v => /\d+ image/.test(v)))
      touch(path.join(photoDir, '.copyright'));
  }
}

module.exports = action;
