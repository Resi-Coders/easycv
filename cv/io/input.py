import requests
from io import BytesIO

import numpy as np
from PIL import Image

from cv.errors.io import ImageDownloadError, InvalidPathError


def open_image(img_dir):
    try:
        img = Image.open(img_dir)
    except IOError as ioe:
        raise InvalidPathError('Invalid Path')
    return np.array(img)


def download_image(url):
    response = requests.get(url, allow_redirects=True)
    if response.status_code != 200:
        raise ImageDownloadError('Invalid Download')
    img = Image.open(BytesIO(response.content))
    return np.array(img)

