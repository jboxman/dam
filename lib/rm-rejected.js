const async = require('async');
const fs = require('fs');
const exec = require('child_process').exec;

const helper = require('./');

/*
  20180827

  Remove files with metadata:

  PickLabel = 1 (rejected)

  The files will persist in git-annex until git annex unused is run.
*/

function action(cmd) {
  process.exit(0);

  async.waterfall([
    helper.gitStagedChanges,
    // Merge in expressions specified on the command line
    async.apply(
      helper.findWithExiftool,
      {
        path: cmd.path,
        dry: false,
        expr: ['$PickLabel eq 1'],
        // Strip the .xmp extension from the result, so foo.jpg.xmp becomes foo.jpg
        extraArgs: `-r -ext 'xmp' -p '\${FilePath;s/\.xmp//}'`
      }),
    async.apply(
      gitRmFiles,
      {
        dry: cmd.dry
      })
    ],
    (err, result) => {
      if(err) {
        console.log(err);
      }
    });
}

module.exports = action;

function gitRmFiles({ dry = true } = {}, files, callback = new Function()) {

  const createGitRmFile = (file) => (next) => {

    const gitCmd = `git rm ${file}`;

    if(dry) {
      console.log(gitCmd);
      process.nextTick(() => next(null));
      return;
    }

    // If the file isn't in the annex, this will fail
    //if(fs.existsSync(file)) {

    exec(gitCmd, (error, stdout, stderr) => {
      if(error) {
        console.log('error');
        if(error.code == 1) {
          console.warn(stderr);
        }
        // fatal: pathspec '<file>' did not match any files
        else if(error.code == 128) {
          console.warn(stderr);
          next(null);
        }
        //next(stderr);
        return;
      }
      // Has a trailing '\n'
      // rm 'photographers/jboxman/2017/12/10/20171210-170401-1000028.jpg.xmp'
      console.log(stdout);
      next(null);
    });
  };

  // Run `git rm` for every valid file extension
  const rmList = files.reduce((accum, file) => {
    accum.push(...helper.fileTypes.map(type => createGitRmFile(`${helper.getBasename(file)}.${type}`)));
    return accum;
  }, []);

  async.waterfall(rmList, (error, result) => callback(null));
}
