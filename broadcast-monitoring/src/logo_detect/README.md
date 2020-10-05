Logo Detection
===

The logo detection functionality analyzes an image (typically an extracted JPG from a video) to extract all logos that can be identified with a pretrained model. When the model successfully identifies logos in an image, the corresponding label, confidence level, and bounding box dimensions a returned for each identified logo.

**Logo Detection** makes use of **AWS Rekognition Custom Label** feature to identify object in images specific to a domain. We consdider this option to be a less time consuming method to identify a logo in a still image.


Usage
---

## Model Control

When a pretrained model is used to detect an image, the model must be explicitly **started** and **stopped** via calls to the Rekognition API prior to and after use. Contained in this directory is the `model_control.py` module which provides the ability to execute these controls.

``` python
# start the model
pipenv run python model_control.py start_model 'arn:aws:rekognition:us-east-1:XXXXXXXXXXXX:project/some-label-project/1580940547880' 'arn:aws:rekognition:us-east-1:XXXXXXXXXXXX:project/some-label-project/version/model_name/1580942074647'
python

# stop the model
pipenv run python model_control.py stop_model 'arn:aws:rekognition:us-east-1:XXXXXXXXXXXX:project/some-label-project/version/model_name/1580942074647'

```
