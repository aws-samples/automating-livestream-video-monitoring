# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: LicenseRef-.amazon.com.-AmznSL-1.0
# Licensed under the Amazon Software License  http://aws.amazon.com/asl/

import argparse
import json
import os
import pathlib
import random
import time
import tempfile

from argparse import ArgumentParser
from datetime import datetime
from io import BytesIO, StringIO
from os.path import isdir, isfile, join
from functools import lru_cache, wraps

import boto3
import imageio
import imgaug as ia
import numpy as np
from imgaug import augmenters as iaa
from imgaug.augmentables.bbs import BoundingBox, BoundingBoxesOnImage
from PIL import Image
from PIL import ImageOps as iops


s3 = boto3.client('s3')

# logo_name_re = re.compile(r'[0-9]*-*(?P<station>[a-z_]+)\.png')
DEFAULT_OUT_SIZE = (1920, 1080)
OVERLAY_PADDING = os.getenv('OVERLAY_PADDING', 20)
DEFAULT_IMAGE_SCALE = (1., 1.)
DEFAULT_IMAGE_SHEAR = (0., 0,)
DEFAULT_IMAGE_ROTATE = (0., 0,)
DEFAULT_OPACITY_RANGE = (-1., -1.)
OPACITY_RANGE_STEP = 0.05


def timeit(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        tic = time.time()
        res = f(*args, **kwargs)
        toc = time.time()

        print(f'{f.__name__} completed in {toc-tic:.1f} s')

        return res

    return wrapper


################################################################################
# Image transforms
################################################################################


def set_alpha(img, sentinel_rgb=None, opacity=None, random_state=None):
    if random_state is None:
        random_state = np.random.default_rng()

    if len(opacity) == 1:
        opacity = opacity[0]
    else:
        mino, maxo = opacity
        opacity = random_state.choice(np.arange(mino, maxo + (.99 * OPACITY_RANGE_STEP), OPACITY_RANGE_STEP))

    # if not specified, take the color of the first pixel as the background color
    # to replace with full transparency
    if sentinel_rgb is None:
        sentinel_rgb = img[0, 0, :3]

    alpha_channel = int(opacity * 255)

    # Make into Numpy array of RGB and get dimensions
    RGB = img[:, :, :3]
    h, w = RGB.shape[:2]

    # Add an alpha channel, with specified opacity
    RGBA = np.dstack((RGB, np.zeros((h, w), dtype=np.uint8) + alpha_channel))

    # Make mask of black pixels - mask is True where image is black
    m_black = (RGBA[:, :, 0:3] == sentinel_rgb).all(2)
    m_alpha = (img[:, :, 3] == 0)

    # Make all pixels matched by mask into transparent ones
    RGBA[m_black] = (0, 0, 0, 0)
    RGBA[m_alpha] = (0, 0, 0, 0)

    # Convert Numnpy array back to PIL Image and save
    return RGBA


def set_alpha_wrapper(opacity_range):
    def inner(images, random_state, parents, hooks):
        results = [set_alpha(img, opacity=opacity_range, random_state=random_state) for img in images]
        return results
    return inner


def create_img_bounding_boxes(img, label=None):
    return BoundingBoxesOnImage([BoundingBox(0, 0, img.shape[1], img.shape[0], label=label)], shape=img.shape)


@timeit
def create_augmented_set(aug, img, bbs, count):
    images = [img] * count
    boxes = [bbs] * count
    images_aug, boxes_aug = aug(images=images, bounding_boxes=boxes)
    return images_aug, boxes_aug


################################################################################
# Ground truth manifest
################################################################################


def build_annotation(label, pos, size):
    left, top = pos
    width, height = size
    return {
        'left': left,
        'top': top,
        'width': width,
        'height': height,
        'annotationType': 'bounding-box',
        'class_id': label
    }


def build_output_manifest_line(s3_bucket, s3_key, img, bounding_boxes, label_map):
    '''Build a groundtruth manifest line from an image and its bounding boxes

    :param s3_bucket: s3 bucket where source media lives
    :param s3_key: key to image object
    :param img: image
    :param bounding_boxes: bounding boxes for labels on the image
    :param label_map: map of index values for each label

    :return a dict representation of an output manifest line
    '''
    img_h, img_w, *_ = img.shape
    # create a reverse map of the class map to convert map[int]str -> map[str]int
    # to allow lookups of annotation value from label name
    r_label_map = {v: k for k, v in label_map.items()}

    def get_bb_info(bb):
        return {
            "pos": (bb.x1_int, bb.y1_int),
            "size": (bb.x2_int - bb.x1_int, bb.y2_int - bb.y1_int),
            "label": r_label_map.get(bb.label)
        }

    manifest_line = {
        'source-ref': f's3://{os.path.join(s3_bucket, s3_key)}',
        'bounding-box': {
            'annotations': [build_annotation(**get_bb_info(bb)) for bb in bounding_boxes],
            'image_size': [{
                "width": img_w,
                "height": img_h,
                "depth": 3
            }]
        },
        'bounding-box-metadata': {
            'class-map': {str(r_label_map[bb.label]): bb.label
                          for bb in bounding_boxes},
            'human-annotated': "yes",
            'objects': [{
                'confidence': 1
            }] * len(bounding_boxes),
            'creation-date': f'{datetime.utcnow().isoformat()[:-3]}Z',
            'type': 'groundtruth/object-detection'
        }
    }
    return manifest_line


################################################################################
# Pipeline Functions
################################################################################

def write_to_file(data):
    tmp_dir = tempfile.mkdtemp(prefix='gen_images_')
    print(f'Writing files to {tmp_dir}')
    for el in data:
        name, img = [el[k] for k in ['name', 'img']]
        imageio.imwrite(os.path.join(tmp_dir, name), img)
        yield el


def generate_manifest_file_to_s3(bucket, prefix, logos, manifest_file='output.manifest'):
    '''
    Higher order function that captures base information to write output manifest
    data to an manifest file and upload it to s3
    '''
    label_map = dict(enumerate({label for label, _ in logos}))

    def build_helper(name, img, bbs, label, **kwargs):
        key = os.path.join(prefix, name)
        return build_output_manifest_line(bucket, key, img, bbs, label_map)

    def write_manifest_data_to_s3(data):
        print(f'Writing data to a manifest: {manifest_file}')
        with StringIO() as buf:
            for el in data:
                line = build_helper(**el)
                buf.write(json.dumps(line) + '\n')
                yield el
            buf.seek(0)
            # write to s3
            key = os.path.join(prefix, manifest_file)
            s3.put_object(Bucket=bucket, Key=key, Body=buf.read())
            print(f'Uploading manifest file to s3://{bucket}/{key}')

    return write_manifest_data_to_s3


def store_image_to_s3(bucket, prefix):
    '''Higher-order function which captures an S3 bucket and key prefix and returns
    a function to write augmented images to S3
    '''
    def write_image_data_to_s3(data):
        for el in data:
            with BytesIO() as buf:
                name, img = [el[k] for k in ['name', 'img']]
                imageio.imwrite(buf, img, format='PNG-PIL')
                buf.seek(0)
                s3.upload_fileobj(buf, bucket, os.path.join(prefix, name))
            yield el

    return write_image_data_to_s3


def progress(data):
    '''Print progress to std out'''
    output_it, output_count = 0, 10
    yield f'Starting processing'
    for i, el in enumerate(data, 1):
        if i % output_count == 0:
            yield f'\t{i} images processed'
            output_it += 1

        if output_it == 10:
            output_count *= 10
            output_it = 0
    yield f'\nImage upload complete! Total: {i}'


def get_file_paths(src_dir):
    return [join(src_dir, f) for f in os.listdir(src_dir) if isfile(join(src_dir, f))]


def get_labeled_images(base_dir, label_filter=None):
    '''Retrieve label name and path data for images(partitioned by label name) under
    base_dir and optionally filter these returned values

    :param base_dir: directory to search
    :param name_filter: when specified, the names of labels to return

    :return yields the name and path of images to process
    '''
    label_names = [fn for fn in os.listdir(base_dir) if isdir(join(base_dir, fn))]

    if label_filter is not None:
        label_names = set(label_filter) & set(label_names)
        print(f'Getting images for the following labels: {list(label_names)}')

    for name in label_names:
        logo_base_path = join(base_dir, name)
        for path in get_file_paths(logo_base_path):
            yield name, path


def generate_augmented_logos(augmenter, images, count=1):
    '''Given a set of images, augment the images using the provided
    Augmenter

    :param augmenter: an imgaug.Augmenter
    :param logos: a collection of images to process
    :param count: number of augmented images to generate per src_image

    :return a dict containing an augmented image, bounding box, and label
    '''

    for label, path in images:
        base_name, ext = os.path.splitext(os.path.basename(path))
        img = imageio.imread(path)
        bbs = create_img_bounding_boxes(img, label=label)
        print(f'\tcreating augmented images for {path}')
        images_aug, boxes_aug = create_augmented_set(augmenter, img, bbs, count)
        print(f'\taugmented images created')
        for i, (img, bbs) in enumerate(zip(images_aug, boxes_aug)):
            yield {'label': label, 'name': f'{base_name}-{i}{ext}', 'img': img, 'bbs': bbs}


def overlay_img_bg(logo, bg, size):
    logo_img = Image.fromarray(logo)
    bg_img = iops.fit(Image.fromarray(bg), size)
    bg_img.paste(logo_img, (0, 0), logo_img)
    return bg_img


@lru_cache(maxsize=32)
def load_bg_image(path):
    return imageio.imread(path)


def overlay_images_backgrounds(overlay_aug, images, backgrounds, out_size, count=1):
    '''Overlay a logo on a background image
    :param images: tuple of (class_name, path) for logo images
    :param backgrounds: set of paths to the background images
    :param out_size: tuple (w,h) with the size of the output image
    :param scale: range of values to scale the logo
    :param count: number of augmented images to generate per source image
    '''
    for label, path in images:
        base_name, ext = os.path.splitext(os.path.basename(path))

        # read in a source image and create bounding boxes
        src_img = imageio.imread(path)
        bbs = create_img_bounding_boxes(src_img, label)

        print(f'\tcreating augmented images for {path}')
        # create a set of augmented images
        aug_images, aug_bbs = create_augmented_set(overlay_aug, src_img, bbs, count)

        # increase the number of the bg_images
        bg_images = [load_bg_image(bg) for bg in random.sample(backgrounds, k=len(backgrounds))]

        grow_factor = count // len(bg_images)
        if count % len(bg_images) != 0:
            grow_factor += 1

        bg_images_repeated = bg_images * grow_factor

        for i, (img, bbs, bg) in enumerate(zip(aug_images, aug_bbs, bg_images_repeated)):
            overlayed_img = overlay_img_bg(img, bg, out_size)
            yield {'label': label, 'name': f'{base_name}-{i}{ext}', 'img': np.array(overlayed_img), 'bbs': bbs}


def build_augmenters(args, augmenters=None):
    ''' Construct a list of augmenters which rely on the arguments handled by the parent parser'''

    if augmenters is None:
        augmenters = []

    opacity_range = args.opacity
    if opacity_range != (-1.0, -1.0):
        # set the alpha channel to a random value
        if opacity_range == (1.0, 1.0):
            opacity_range = (1.0)
        augmenters.insert(0, iaa.Lambda(func_images=set_alpha_wrapper(opacity_range)))

    scale = args.scale
    if scale != (1.0, 1.0):
        augmenters.append(iaa.Affine(scale=scale))    # scale the image between 20% to 125% of its original size

    rotate = args.rotate
    if rotate != (0.0, 0.0):
        augmenters.append(iaa.Rotate(rotate))    # rotate the image somewhere in the range of -10.0 - 10.0 deg

    shear = args.shear
    if shear != (0.0, 0.0):
        augmenters.append(iaa.ShearX(shear))    # rotate the image somewhere in the range of -10.0 - 10.0 deg

    noise = args.noise
    if noise != (0, 0):
        augmenters.append(iaa.AdditiveGaussianNoise(scale=noise))

    grayscale = args.grayscale
    if grayscale != (0.0, 1.0):
        augmenters.append(iaa.WithChannels([0, 1, 2], iaa.Grayscale(alpha=(0.0, 1.0))))

    return augmenters


def generate(args):
    '''
    Build a dataset augmenting logo images found under base_dir
    and filter images by their collection name
    '''
    seq = iaa.Sequential(build_augmenters(args))

    logos = list(get_labeled_images(pathlib.Path(args.base_dir).resolve(), args.label_filter))
    data = generate_augmented_logos(seq, logos, args.count)

    process_command(args, logos, data)


def overlay(args):
    '''
    Build a dataset augmenting logos images found under a base_dir
    to be overlayed on a random bg image
    '''
    logos = list(get_labeled_images(pathlib.Path(args.base_dir).resolve(), args.label_filter))
    bg_paths = get_file_paths(args.background_dir)

    out_size = args.out_size

    # convert the image to a set size
    base = [iaa.Resize({"shorter-side": 256, "longer-side": "keep-aspect-ratio"})]

    augmenters = build_augmenters(args, augmenters=base)
    augmenters.append(iaa.PadToFixedSize(width=out_size[0], height=out_size[1]))

    overlay_aug = iaa.Sequential(augmenters)

    data = overlay_images_backgrounds(overlay_aug, logos, bg_paths, out_size, args.count)

    process_command(args, logos, data)


def process_command(args, logos, data):
    ia.seed(args.seed)
    prefix = os.path.join(args.s3_key_prefix, datetime.utcnow().strftime('%Y%m%d-%H%M%S'))

    if args.local:
        pipeline = write_to_file(data)
    else:
        generate_manifest = generate_manifest_file_to_s3(args.s3_bucket, prefix, logos)
        upload_to_s3 = store_image_to_s3(args.s3_bucket, prefix)

        pipeline = upload_to_s3(generate_manifest(data))

    for res in progress(pipeline):
        print(res)


# Courtesy of http://stackoverflow.com/a/10551190 with env-var retrieval fixed
class EnvDefault(argparse.Action):
    """An argparse action class that auto-sets missing default values from env
    vars. Defaults to requiring the argument."""
    def __init__(self, envvar, required=True, default=None, **kwargs):
        if not default and envvar:
            if envvar in os.environ:
                default = os.environ[envvar]
        if required and default:
            required = False
        super(EnvDefault, self).__init__(default=default, required=required, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, values)


# functional sugar for the above
def env_default(envvar):
    def wrapper(**kwargs):
        return EnvDefault(envvar, **kwargs)

    return wrapper


def build_parent_parser():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('base_dir', help='a directory containing subdirectories of logo images')

    parser.add_argument('--local', action='store_true')

    parser.add_argument(
        '--bucket',
        '--s3-bucket',
        dest='s3_bucket',
        action=env_default('S3_BUCKET'),
        help='S3 bucket name to store results; defualts to env variable when not specified'
    )
    parser.add_argument(
        '--s3-key-prefix', default='images', help='prefix to use when generating keys to store objects'
    )
    parser.add_argument(
        '--count', type=int, default=10, help='number of augmented images to generate per source image'
    )
    parser.add_argument(
        '--filter',
        dest='label_filter',
        nargs='+',
        metavar='label_name',
        help='labels(subdirectory names) under base_dir to filter'
    )
    parser.add_argument('--seed', default=314159, nargs='?', metavar='seed', type=int, help='random seed value')
    parser.add_argument(
        '--rotate',
        default=DEFAULT_IMAGE_ROTATE,
        metavar=('min', 'max'),
        nargs=2,
        type=float,
        help=f'rotation range in degrees default: {DEFAULT_IMAGE_ROTATE}'
    )
    parser.add_argument(
        '--scale',
        default=DEFAULT_IMAGE_SCALE,
        metavar=('min', 'max'),
        nargs=2,
        type=float,
        help=f'a range to scale an image default: {DEFAULT_IMAGE_SCALE}'
    )

    parser.add_argument(
        '--shear',
        default=DEFAULT_IMAGE_SHEAR,
        metavar=('min', 'max'),
        nargs=2,
        type=float,
        help=f'a range to shear an image default: {DEFAULT_IMAGE_SHEAR}'
    )

    parser.add_argument(
        '--opacity',
        default=DEFAULT_OPACITY_RANGE,
        metavar=('min', 'max'),
        nargs=2,
        type=float,
        help=f'an opacity range to set the opacity of an imagea default: {DEFAULT_OPACITY_RANGE}'
    )

    parser.add_argument(
        '--noise',
        default=(0, 0),
        metavar=('min', 'max'),
        nargs=2,
        type=float,
        help=f'gaussian noise to add to the logos default: (0, 0)'
    )

    parser.add_argument(
        '--grayscale',
        default=(0.0, 1.0),
        metavar=('min', 'max'),
        nargs=2,
        type=float,
        help=f'randomly apply the grayscale augmenter default: (0, 0)'
    )

    return parser


def main():
    parser = ArgumentParser(
        usage='generate-logo-image ', description="process logo images to create Rekognition custom labels"
    )

    parent_parser = build_parent_parser()
    subparsers = parser.add_subparsers(title='sub-commands', description='valid subcommands')

    # create sub-parser for generate command
    generate_parser = subparsers.add_parser('generate', help='generate help', parents=[parent_parser])
    generate_parser.set_defaults(func=generate)

    # create sub-parser for overlay command
    overlay_parser = subparsers.add_parser('overlay', help='overlay help', parents=[parent_parser])
    overlay_parser.set_defaults(func=overlay)
    overlay_parser.add_argument(
        'background_dir',
        help='directory containing subdirectories of background images')

    overlay_parser.add_argument(
        '--out_size',
        default=DEFAULT_OUT_SIZE,
        metavar=('min', 'max'),
        nargs=2,
        type=int,
        help=f'size of the output overlay image default: {DEFAULT_OUT_SIZE}'
    )

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
