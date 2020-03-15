const fs = require('fs');
const path = require('path');
const dir = require('node-dir');

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

  if(! fs.existsSync(path.join(photoDir, `.ingest`))) {
    console.error('Files must have been ingested.');
    return;
  }

  const files = await dir.promiseFiles(photoDir)
    .then(function(files) {
      const includeRegex = /(_original|~)$/i;
      return files.filter(file => includeRegex.test(file));
    });

  for(const file of files) {
    if(fs.existsSync(file)) {
      if(dry) {
        dryLog(`Unlinking ${path.basename(file)}`);
        continue;
      }

      runLog(`Unlinking ${path.basename(file)}`);
      try {
        fs.unlinkSync(file);
      }
      catch(err) {
        console.error(e);
        success = false;
      }
    }
  }

  if(!dry && success)
    touch(path.join(photoDir, '.clean'));
}

module.exports = action;
