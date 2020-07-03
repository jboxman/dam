const fs = require('fs');
const path = require('path');
const mkdirp = require('mkdirp');
const dir = require('node-dir');

//const { top_dir, Fn } = require('./');
const { loadConfig } = require('./config');

const {
  dryLog,
  runLog
} = require('./');

const config = loadConfig();

const photoDir = path.join(config.stagingDir, config.defaultUser);
const targetDir = path.join(config.digikamDir, config.defaultUser);

async function action(cmd) {
  const { dry, fileSync: doFileSync, metaSync: doMetaSync } = cmd;
  if(!doFileSync && !doMetaSync) {
    doFileSync = true;
    doMetaSync = true;
  }

  try {
    if(!dry)
      mkdirp.sync(targetDir);
  }
  catch(e) {
    console.log(e);
    process.exit(1);
  }

  if(doFileSync)
    await fileSync({ dry }).catch(e => console.log(e));
  if(doMetaSync)
    await metaSync({ dry }).catch(e => console.log(e));
}

async function fileSync({ dry = true } = {}) {
  const includeRegex = /\.jpg$/i;
  let sourceFiles;
  let targetFiles;

  try {
    sourceFiles = await dir.promiseFiles(photoDir)
      .then(files => {
        return files.filter(file => includeRegex.test(file));
      });
  }
  catch(e) {
    console.log(e);
    process.exit(1);
  }

  try {
    targetFiles = await dir.promiseFiles(targetDir)
      .then(files => {
        // Flag for removal any files no longer tagged for inclusion
        return files
          .filter(file => includeRegex.test(file))
          .filter(file => {
            let testpath = file.replace(targetDir, photoDir);
            return !sourceFiles.includes(testpath);
          });
      });
  }
  catch(e) {
    console.log(e);
    process.exit(1);
  }

  await sourceFiles.reduce(async function(p, v) {
    await p;
    return createLink(v, dry);
  }, Promise.resolve());

  for(targetFile of targetFiles) {
    if(!fs.existsSync(targetFile))
      continue;

    const msg = 'Unlink: ' + targetFile;
    dry ? dryLog(msg) : runLog(msg);

    if(!dry)
      fs.unlinkSync(targetFile);
  }
}

// TODO - abstact; this applies to meta and file
async function metaSync({ dry = true } = {}) {
  const includeRegex = /\.xmp$/i;
  let sourceFiles;
  let targetFiles;

  // reverse of fileSync
  try {
    sourceFiles = await dir.promiseFiles(targetDir)
      .then(files => {
        return files.filter(file => includeRegex.test(file));
      });
  }
  catch(e) {
    console.log(e);
    process.exit(1);
  }

  // reverse of fileSync
  try {
    targetFiles = await dir.promiseFiles(photoDir)
      .then(files => {
        // Flag for removal any files no longer tagged for inclusion
        return files
          .filter(file => includeRegex.test(file))
          .filter(file => {
            let testpath = file.replace(photoDir, targetDir);
            return !sourceFiles.includes(testpath);
          });
      });
  }
  catch(e) {
    console.log(e);
    process.exit(1);
  }

  for(const file of sourceFiles) {
    let destPath = file.replace(targetDir, photoDir);

    const msg = `Sync: ${destPath.replace(photoDir, '<digikamDir>/...')}`;
    dry ? dryLog(msg) : runLog(msg);

    if(!dry)
      fs.copyFileSync(file, destPath);
  }

  for(targetFile of targetFiles) {
    if(!fs.existsSync(targetFile))
      continue;

    const msg = `Unlink: ${targetFile.replace(photoDir, '<photoDir>/...')}`;
    dry ? dryLog(msg) : runLog(msg);

    if(!dry)
      fs.unlinkSync(targetFile);
  }

}

// Resolve symlink, because it is up to the file system implementation
// whether the hardlink is to the symlink or target.
// https://stackoverflow.com/questions/33361600/can-we-create-a-hard-link-to-a-symbolic-link-in-unix

async function createLink(srcFile, dry = true) {
  const srcFileReal = fs.realpathSync(srcFile);
  const dstFile = srcFile.replace(photoDir, targetDir);
  const dstPath = path.dirname(dstFile);

  if(fs.existsSync(dstFile))
    return;

  const msg = `Create: ${dstFile}`;
  dry ? dryLog(msg) : runLog(msg);

  if(dry)
    return;

  try {
    mkdirp.sync(dstPath);
  }
  catch(e) {
    console.log(e);
    process.exit(1);
  }

  try {
    fs.linkSync(srcFileReal, dstFile);
  }
  catch(e) {
    console.log(e);
    process.exit(1);
  }
}

module.exports = action;
