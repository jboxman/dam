const path = require('path');
const {
  findWithExiftool,
  runLog
} = require('.');

async function action(sourceDir, targetDir) {
  // confirm dirs exist

  const commonOptions = {
    dry: false,
    fileTypes: ['jpg'],
    extraArgs: `-r -d %Y%m%d%H%M%S -p '\${Directory}^\${FileName}^\${DateTimeOriginal}\${SubsecTimeOriginal}-\${DirectoryNumber}-\${FileNumber}'`
  };

  const sourceFiles = await findWithExiftool({
    ...commonOptions,
    path: sourceDir
  }).then(files => files.reduce(fn, {}));

  runLog(`${sourceDir}: ${Object.keys(sourceFiles).length} files`);

  const targetFiles = await findWithExiftool({
    ...commonOptions,
    path: targetDir
  }).then(files => files.reduce(fn, {}));

  runLog(`${targetDir}: ${Object.keys(targetFiles).length} files`);

  //console.log(sourceFiles);
  // Split on dir, filename, key
  // Confirm if source file is in target dir

  const missing = Object.keys(sourceFiles)
    .filter(entry => !targetFiles[entry]);

  for(const key of missing) {
    runLog(`Missing ${sourceFiles[key].path}`);
  }
}

function fn(dict, item) {
  return {
    ...dict,
    ...byKey(item)
  };
}

function byKey(v) {
  let [ dirname, filename, stamp ] = v.split('^');

  //console.log(`${stamp}.${path.basename(filename)}`);

  return {
    [`${stamp}`]: {
      filename,
      dirname,
      path: path.join(dirname, filename)
    }
  }
}

module.exports = action;
