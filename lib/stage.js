const util = require('util');
const fs = require('fs');
const path = require('path');
const exec = util.promisify(require('child_process').exec);
const eol = require('eol');

const { loadConfig, exiftoolConfigFile } = require('./config');
const {
  touch,
  dryLog,
  runLog
} = require('./');

const config = loadConfig();

// TODO - Make configurable
const stagingDir = path.join(config.stagingDir, config.defaultUser);

async function action(photoDir, cmd) {
  let logLines;

  if(!readyToStage(photoDir)('rotate') && !readyToStage(photoDir)('copyright')) {
    console.error('Files must have attribution and rotation applied.');
    return;
  }

  if(!fs.existsSync(exiftoolConfigFile)) {
    console.error(`${exiftoolConfigFile} does not exist!`);
    process.exit(1);
  }

  if(! fs.existsSync(photoDir)) {
    console.error(`Directory does not exist: ${photoDir}`);
    process.exit(1);
  }

  await renameWithExiftool({
    expr: ['defined $CreateDate'],
    fileTypes: ['jpg', 'nef'],
    path: photoDir,
    dry: cmd.dry
  });

  if(! cmd.dry)
    runLog('Enter `git annex add` to add the files to the annex.');
}

async function renameWithExiftool(options = {}) {
  let stdout, stderr;
  const staging_path_prefix = `${stagingDir}/%Y/%m/%d/`;
  const defaultOptions = {
    dry: true,
    expr: [],
    fileTypes: []
  };
  options = Object.assign(defaultOptions, options);

  // Perform the renaming
  if(! options.dry) {
    options.target = 'FileName';
  }
  else {
    options.target = 'TestName';
  }

  const baseArgs = [
    `-config ${exiftoolConfigFile}`,
    '-m',
    `'-${options.target}<\${CreateDate}\${MySequenceNum}.%le'`,
    `-d '${staging_path_prefix}%Y%m%d-%H%M%S'`
  ].join(' ');

  const conditional = options.expr.map(xpression => `-if '${xpression}'`).join(' ');
  const extensions = options.fileTypes.map(fileType => `-ext ${fileType}`).join(' ');

  let args;
  args = `exiftool ${baseArgs} ${extensions} ${conditional} ${options.path}`;
  options.dry ? dryLog(`${args}`) : runLog(`${args}`);

  try {
    ({ stdout, stderr } = await exec(`${args}`, { maxBuffer: 1024 * 1024 }));
  }
  catch(err) {
    console.log(err);
    process.exit(1);
  }

  output = eol.split(stdout).slice(0, -1);

  // RUN
  // [ '    1 directories scanned',
  // '    1 directories created',
  // '  180 image files updated' ]

  // Matches dry run output only
  if(options.dry) {
    logLines = output
      .filter(line => /-->/.test(line));

    logLines.forEach(line => {
      dryLog(`${line}`);
    });

    dryLog(`Files matched: ${logLines.length}`);
  }
  else {
    output.map(v => v.trim())
      .forEach(line => {
        runLog(line);
      });

    if(output.some(v => /\d+ image/.test(v)))
      touch(path.join(options.path, '.ingest'));
  }

}

function readyToStage(photoDir) {
  return function(touch) {
    if(fs.existsSync(path.join(photoDir, `.${touch}`)))
      return true;

    return false;
  }
}

module.exports = action;
