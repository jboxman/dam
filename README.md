Purpose
----

Proof of concept integrating [digiKam](https://www.digikam.org) and [git-annex](https://git-annex.branchable.com).

Because of how `git-annex` works, it isn't practical to use the working directory with digiKam:

- Leaving all files in the `git-annex` repo unlocked doubles disk space usage, and using `thin` mode instead puts data at risk.
- If the files are locked, digiKam cannot save XMP sidecar files; digiKam resolves symlinks, but `git-annex` does not allow files to be created in the `.git/annex` directory.

So this proof of concept implements a bi-directional sync between two directory trees.

- `stagingDir`: Directory of the `git` repo configured with `git-annex`
- `digikamDir`: Directory for digiKam files, including the SQLite database

Additionally, the PoC implements:

- Ingest image files into `photographers/<USER>/YYYY/MM/DD`
- Apply copyright metadata assignment to JPEG and NEF files
- Apply image (JPEG) data rotation, with EXIF orientation reset

Because digiKam is best for organizing photos, all tagging is managed there. So once ingested, the files are never moved or renamed again.

This is a working PoC. It includes limited error checks and no unit tests, so use at your own risk. But you're already managing your photos with `git-annex`, with data replicated to multiple storage devices anyway, right?

Commands
----

The following commands are available:

```
dam --help
Usage: dam [options] [command]

Options:
  -h, --help                             output usage information

Commands:
  what-can <photo-dir>                   List valid actions for a dir
  ingest [options] <photo-dir>           Move files into staging directory
  apply-copyright [options] <photo-dir>  Apply copyright to images
  apply-rotation [options] <photo-dir>   Rotate images and reset EXIF orientation flag
  sync [options]                         Sync data between photo and digiKam directories
  cleanup [options] <photo-dir>          Clean up backup files
  compare <source-dir> <target-dir>      Compare files in <source-dir> and <target-dir>
  rm-rejected [options]                  (not implemented) Remove files marked as rejected by digiKam
```

Configuration
----

The configuration file lives in `~/.dam`.

Defaults:

```js
const defaultUser = process.env['USER'];
const defaultUserDir = process.env['HOME'];
const configDir = path.join(defaultUserDir, '.dam');
const configFile = path.join(configDir, 'config.json');
const exiftoolConfigFile = path.join(configDir, 'exiftool.conf');

```

Defaults:

```js
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

```

Example configuration for [ExifTool](https://exiftool.org). The user defined `MySequenceNum` is used to create a unique filename for each image when ingesting.

```
%Image::ExifTool::UserDefined = (
  # For XMP files, digiKam expects FILENAME.EXT.XMP
  'Image::ExifTool::Composite' => {
    Extension => {
      Require => {
        0 => 'FileName',
      },
      ValueConv => sub {
        my $val = shift;
        my $fn = @$val[0];

        if($fn =~ /(\.[^.]+)(\.xmp)\z/) {
          return $1;
        }
        return "";
      },
    },

    MySequenceNum => {
      Desire => {
        0 => 'FileNumber',
        1 => 'DirectoryNumber',
        2 => 'Model',
      },
      ValueConv => sub {
        my $val = shift;
        my $sep = '-';
        my ($fileno, $dirno, $model) = @$val;

        # These lack a sequence number at all.
        # With the model # may not need this.
        #if($model =~ /Nexus 4/) { return '0' x 7; }
        #if($model =~ /COOLPIX P100/) { return '0' x 7; }
        #if($model =~ /PowerShot A60/) { return $sep . $fileno; }
        if($model =~ /NIKON D3100/) {
          return sprintf('%s%03d%04d' , $sep, $dirno, $fileno);
        }

        return "";
      },
    },

  },
);
```

Examples
----

Example of the annex repo:

```
── photographers
   ├── jasonb
   │   ├── 2004
   │   │   ├── 06
   │   │   │   ├── 16
   │   │   │   │   ├── 20040616-004528.jpg -> ../../../../../.git/annex/objects/xG/32/WORM-s256444-m1087361128--photographers%jboxman%2004%06%16%20040616-004528.jpg/WORM-s256444-m1087361128--photographers%jboxman%2004%06%16%20040616-004528.jpg
   │   │   │   │   ├── 20040616-004528.jpg.json
   │   │   │   │   └── 20040616-004528.jpg.xmp
```

Example of the digiKam repo:

```
── db
│   ├── digikam4.db
│   ├── recognition.db
│   ├── similarity.db
│   └── thumbnails-digikam.db
── photographers
    └── jasonb
        ├── 2004
        │   ├── 06
        │   │   ├── 16
        │   │   │   ├── 20040616-004528.jpg
        │   │   │   └── 20040616-004528.jpg.xmp
```

Known issues
----

- When `exiftool` exits with a nonzero code, the error is not handled usefully
- When renaming files with `exiftool`, a filename collision causes an error

TODO
----

- Cleanup code
- Add what-config to expose the runtime configuration

