#! /usr/bin/bash

BUILD_DIR=${BUILD_DIR:-.build}

rm -rf ${BUILD_DIR}

mkdir -p $BUILD_DIR/layer/bin
rm -rf $BUILD_DIR/ffmpeg*
pushd $BUILD_DIR
curl https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz | tar xJ
popd
mv $BUILD_DIR/ffmpeg*/ffmpeg $BUILD_DIR/ffmpeg*/ffprobe $BUILD_DIR/layer/bin/
