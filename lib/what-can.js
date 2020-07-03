const fs = require('fs');
const path = require('path');
const dir = require('node-dir');

// For a dir, list available actions:
// copyright, rotation, ingest, or cleanup
// Support recursive for a directory

const {
  runLog
} = require('./');

const actions = {
  ROTATE: '.rotate',
  COPYRIGHT: '.copyright',
  INGEST: '.ingest',
  CLEAN: '.clean'
};

async function action(photoDir, cmd) {
  // TODO - recursive

  if(! fs.existsSync(photoDir)) {
    console.error(`Directory does not exist: ${photoDir}`);
    process.exit(1);
  }

  const dots = await dir.promiseFiles(photoDir)
    .then(function(files) {
      const includeRegex = /^\./i;
      return files
        .filter(file => includeRegex.test(path.basename(file)))
        .map(file => path.basename(file));
    });

  if(allDone(dots)) {
    runLog('All valid actions for an import dir are complete.')
    return;
  }

  // This needs to be, if the dot can't be found, that action is available
  const done = [];
  for(const dot of dots) {
    const ok = Object.entries(actions).find(([ action, file ]) => file == dot);
    if(ok)
      done.push(dot);
  }

  const available = Object.entries(actions)
    .filter(([ action, file ]) => !done.includes(file))
    .reduce((accum, entry) => {
      return [ ...accum, entry[0] ];
    }, []);

  runLog(`Available actions: ${available.join(', ')}`);
}

function allDone(dots = []) {
  let ok = true;
  for(const v of Object.values(actions)) {
    if(! dots.includes(v))
      ok = false;
  }

  return ok;
}

module.exports = action;
