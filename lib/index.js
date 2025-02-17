const util = require('util');
const exec = util.promisify(require('child_process').exec);
const eol = require('eol');
const path = require('path');
const { closeSync, openSync, utimesSync } = require('fs');

const top_dir = '/Users/jasonb/Self/repos/photos/photographers/jboxman';
const ROOT = path.join(__dirname, '../..');
const fileTypes = ['jpg.xmp', 'jpg', 'nef', 'jpg.json'];
const Fn = () => {};

const log = msgType => msg => console.log(`[${msgType.toUpperCase()}] ${msg}`);
const dryLog = log('dry');
const runLog = log('run');

async function findWithExiftool(options = {}) {
  let cmd, stdout, stderr;
  let output;

  const defaultOptions = {
    path: top_dir,
    expr: [],
    extraArgs: '',
    fileTypes: [],
    dry: true
  };

  options = Object.assign({}, defaultOptions, options);

  options.expr = Array.isArray(options.expr) ? options.expr : [];
  options.path = typeof options.path == 'string' ? options.path : top_dir;

  // This mode will ignore minor warnings, rather than force exiftool to exit with an error
  const baseArgs = '-m';
  const conditional = options.expr.map(xpression => `-if '${xpression}'`).join(' ')
  const extensions = options.fileTypes.map(fileType => `-ext ${fileType}`).join(' ');

  cmd = `exiftool ${baseArgs} ${options.extraArgs} ${conditional} ${extensions} ${options.path}`;
  options.dry ? dryLog(cmd) : runLog(cmd);

  // Guarantee non-destructive by not running at all
  if(options.dry) {
    return [];
  }

  try {
    ({ stdout, stderr } = await exec(`${cmd}`, {maxBuffer: 1024 * 1024}));
  }
  catch(err) {
    console.warn(err);
    console.warn(stderr);
    // This isn't necessarily fatal; It may be no files matched or some could not be read.
    //process.exit(1);
    ({ stdout, stderr } = err);
  }

  output = eol.split(stdout).slice(0, -1);

  return output;
}

function gitStagedChanges(callback = new Function()) {
  exec(`git diff --cached --exit-code`, {maxBuffer: 1024 * 1024}, (error, stdout, stderr) => {
    if(error) {
      if(error.code == 129) {
        console.warn('Must be within a git repository.')
      }
      if(error.code == 1) {
        console.warn('Any staged changes must be committed prior to running this command.')
      }
      callback(error);
      return;
    }

    callback(null);
  });
}

function getBasename(fsPath) {
  return path.join(path.dirname(fsPath), path.basename(fsPath, path.extname(fsPath)));
}

function sortByFilename(a, b) {
  return path.basename(a).localeCompare(path.basename(b));
}

// https://remarkablemark.org/blog/2017/12/17/touch-file-nodejs/
// sync
const touch = path => {
  const time = new Date();
  try {
    utimesSync(path, time, time);
  } catch (err) {
    closeSync(openSync(path, 'w'));
  }
}

module.exports = {
  Fn,
  ROOT,
  top_dir,
  findWithExiftool,
  gitStagedChanges,
  getBasename,
  fileTypes,
  dryLog,
  runLog,
  touch
};
