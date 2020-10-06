# Helper scripts

If not using `pipenv`, before running the scripts, install classes from `sharedlib`

```bash
pip  --no-cache-dir install -e ../sharedlib
```

If using `pipenv`, simply run `pipenv install` in the `broadcast-monitoring` directory.

### Load expected schedule metadata to DDB table

```shell script
python scripts/load_csv_to_ddb.py scripts/schedule.csv <table-name>
```

### Generate Logos

The generate logos script is used to create images by augmenting a set of logo images to provide data to train a model for custom label detection. This script also uploads these images to s3 and creates a Ground Truth manifest file with bounding boxes annotations for the areas of interest in the images.

#### TL;DR

Let's generate some images. This script accepts a number of parameters to influence its behavior.

As a pre-requisite, you'll need source image data. This data can be downloaded from s3 with the following command:

```shell
# To generate logos with opacity changed and scaled, execute the following from # the top level of this repo
aws s3 sync s3://aws-rnd-broadcast-maas-data/images/station_logos ~/tmp/data/station_logos
```

Basic usage is as follows:

```
pipenv run python scripts/generate-logo-images.py ~/tmp/data/station_logos --filter 'channel_one' 'amazon_prime_video' 'bad_logo' 'good_logo' --count 100
```

More in depth usage details can be found using the `--help` option:

```
> pipenv run python scripts/generate-logo-images.py --help

Loading .env environment variables…
usage: generate-logo-image [options] logo_src_dir

Build a dataset augmenting logo images found under base_dir and filter images
by their collection name

positional arguments:
  image_dir             a directory containing subdirectories of logo images

optional arguments:
  -h, --help            show this help message and exit
  --bucket S3_BUCKET, --s3-bucket S3_BUCKET
                        S3 bucket name to store results; defualts to env
                        variable when not specified
  --s3-key-prefix S3_KEY_PREFIX
                        prefix to use when generating keys to store objects
  --count COUNT         number of augmented images to generate per source
                        image
  --filter label_name [label_name ...]
                        labels(subdirectory names) under base_dir to filter
  --seed [seed]         random seed value
  --rotate min max      rotation range in degrees default: (-15.0, 15.0)
  --scale min max       a range to scale an image default: (0.14, 0.14)

```

```shell
# To generate images with logos overlayed with random size, execute the
# following from the top level of this repo

pipenv python scripts/generate-logo-images.py ~/tmp/data/teams ~/tmp/data/background/soccer --filter 'arsenal', 'chelsea', 'bornemouth', 'norwich_city', 'aston_villa' --count 500 --scale 0.05 0.35
```

Let's unpack the parts of this command:

1. `pipenv run python scripts/generate-logo-images.py` - Exectues the script in a python environment with known dependencies

1. `data/png` - a directory containing pngs

```
/home/dev/tmp/data/station_logos
├── amazon_prime_video
│   └── amazon_prime_video.png
├── bad_logo
│   └── bad_logo.png
...
└── netflix
   ├── 001-netflix.png
   └── 002-netflix.png
```

1. `~/tmp/data/png/background/` - a directory containing bag images

1. `--filter 'good_logo', 'bad_logo', 'channel_one', 'amazon_prime_video'` - a subset of logos to generate images for. The filename for the .png will also be the label

1. `--count 10` - Then number of images to generate per label

#### Output

This script outputs it general progress in generating the set of images. In the event of an error, exception info will be logged out.

When complete, the script outputs the location of the generated Ground Truth manifest file.

```script
Uploading output.manifest to s3: s3://aws-rnd-broadcast-maas-data/images/20200306-233841/output.manifest
```

#### Notes

The script outputs general progress as it's generating and uploading images to S3. When possible, run this script on an EC2 instance to benefit from the configurable CPU settings and accelerated network speeds.

#### Concepts

There were two primary objectives regarding image detection with this project. The first was to recognize a station logo from a still frame extracted from a video. The second goal was to detect English Premier League(EPL) logos, and more broadly team logos, again from still frames extracted from video. Each of these objectives vary slightly in the properties of the logo to be detected.

##### Station Logos

After reviewing test footage, we confirmed that logos typically varied along two dimensions: position and opacity. This necessitated building a method to generate synthetic data to train an ML model using AWS Recognition Custom Labels.

##### Team Logos

Team logos are used as a secondary method to detect teams playing in a video stream. Team logos primarily vary in size and position. Training a model to detect logos again necessitated a dataset that would be difficult to acquire, so a synthetic dataset was used.

#### Process

- Download the necessary logos. Where possible, use an SVG as a starting point.
- SVGs were converted to PNGs using **CairoSVG** with a virtual environment created using piping
  ````
  pipenv run cairosvg ../broadcast-monitoring/data/svg amazon_prime_video.svg -o ../broadcast-monitoring/data/png/amazon_prime_video.png
  ````
- Using the `generate-logo-images.py` script images were generated by auto clearing the background color, setting the logo to a random opacity, scaling the logo, and overlaying it on a random background image from a set of images.
- With AWS Recognition custom labels, each model was trained by splitting the dataset with a 80/20 train/test split.
