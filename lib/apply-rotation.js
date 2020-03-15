const util = require('util');
const exec = util.promisify(require('child_process').exec);
const path = require('path');
const fs = require('fs');
const dir = require('node-dir');
const eol = require('eol');

const {
  touch,
  dryLog,
  runLog
} = require('./');

async function action(photoDir, cmd) {
  let success = true;
  const { dry } = cmd;

  if(! fs.existsSync(photoDir)) {
    console.error(`Directory does not exist: ${photoDir}`);
    process.exit(1);
  }

  const files = await dir.promiseFiles(photoDir)
    .then(function(files) {
      const includeRegex = /\.jpg$/i;
      return files.filter(file => includeRegex.test(file));
    });

  // Rotate inplace using EXIF information, creating a backup and preserving timestamps
  for(const file of files) {
    const cmd = `exiftran -aipb "${file}"`;

    if(! dry) {
      try {
        // Produces no output on success
        const { stdout, stderr } = await exec(cmd);
        runLog(`Trying to rotate ${path.basename(file)}`);
      }
      catch(e) {
        console.error(e);
        if(err.errno == 'EAGAIN') {
          process.exit(1);
        }
        success = false;
      }
    }
    else {
      dryLog(`exiftran -aipb ${path.basename(file)}`);
    }
  }

  if(! dry && success)
    touch(path.join(photoDir, '.rotate'));

}

module.exports = action;
