from matplotlib.widgets import RectangleSelector, EllipseSelector
import matplotlib.pyplot as plt
import matplotlib as mpl
import os
import cv2
import numpy as np


from easycv.transforms.base import Transform
from easycv.validators import Number, List, Type
from easycv.errors import InvalidSelectionError

from easycv.io.output import prepare_image_to_output


class Select(Transform):
    """
    Select is a transform that allows the user to select a shape in an image. Currently \
    supported shapes:

    \t**∙ rectangle** - Rectangle Shape\n
    \t**∙ point** - Point\n
    \t**∙ ellipse** - Ellipse Shape\n

    :param n: Number of points to select
    :type n: :class:`int`
"""

    methods = {
        "rectangle": {"arguments": [], "outputs": ["rectangle"]},
        "point": {"arguments": ["n"], "outputs": ["points"]},
        "ellipse": {"arguments": [], "outputs": ["ellipse"]},
    }
    default_method = "rectangle"

    arguments = {
        "n": Number(only_integer=True, min_value=0, default=2),
    }

    outputs = {
        # rectangle
        "rectangle": List(
            List(Number(min_value=0, only_integer=True), length=2), length=2
        ),
        # ellipse
        "ellipse": List(
            List(Number(only_integer=True, min_value=0), length=2),
            Number(min_value=0, only_integer=True),
            Number(min_value=0, only_integer=True),
        ),
        # point
        "points": List(List(Number(min_value=0, only_integer=True), length=2)),
    }

    def process(self, image, **kwargs):
        if "DISPLAY" not in os.environ:
            raise Exception("Can't run selectors without a display!")

        mpl.use("Qt5Agg")

        fig, current_ax = plt.subplots()
        plt.tick_params(
            axis="both",
            which="both",
            bottom=False,
            top=False,
            left=False,
            right=False,
            labelbottom=False,
            labelleft=False,
        )

        def empty_callback(e1, e2):
            pass

        def selector(event):
            if event.key in ["Q", "q"]:
                plt.close(fig)

        res = []
        current_ax.imshow(prepare_image_to_output(image))
        plt.gcf().canvas.set_window_title("Selector")

        if kwargs["method"] == "rectangle":
            selector.S = RectangleSelector(
                current_ax,
                empty_callback,
                useblit=True,
                button=[1, 3],
                minspanx=5,
                minspany=5,
                spancoords="pixels",
                interactive=True,
            )
        elif kwargs["method"] == "ellipse":
            selector.S = EllipseSelector(
                current_ax,
                empty_callback,
                drawtype="box",
                interactive=True,
                useblit=True,
            )
        else:

            def onclick(event):
                if event.xdata is not None and event.ydata is not None:
                    res.append((int(event.xdata), int(event.ydata)))
                    plt.plot(
                        event.xdata, event.ydata, marker="o", color="cyan", markersize=4
                    )
                    fig.canvas.draw()
                    if len(res) == kwargs["n"]:
                        plt.close(fig)

            plt.connect("button_press_event", onclick)

        plt.connect("key_press_event", selector)
        plt.show(block=True)

        if kwargs["method"] == "rectangle":
            x, y = selector.S.to_draw.get_xy()
            x = int(round(x))
            y = int(round(y))
            width = int(round(selector.S.to_draw.get_width()))
            height = int(round(selector.S.to_draw.get_height()))

            if width == 0 or height == 0:
                raise InvalidSelectionError("Must select a rectangle.")

            return {"rectangle": [(x, y), (x + width, y + height)]}

        elif kwargs["method"] == "ellipse":
            width = int(round(selector.S.to_draw.width))
            height = int(round(selector.S.to_draw.height))
            center = [int(round(x)) for x in selector.S.to_draw.get_center()]
            if width == 0 or height == 0:
                raise InvalidSelectionError("Must select an ellipse.")
            return {"ellipse": [tuple(center), int(width / 2), int(height / 2)]}
        else:
            if len(res) != kwargs["n"]:
                raise InvalidSelectionError(
                    "Must select {} points.".format(kwargs["n"])
                )
            return {"points": res}


class Mask(Transform):
    """
    Mask is a transform that allows the user to create a mask in an image.

    :param brush: Brush size, defaults to 20
    :type brush: :class:`int`, optional

    :param color: Mask color, defaults to (0,255,0)
    :type color: :class:`list`, optional
    """

    arguments = {
        "brush": Number(only_integer=True, min_value=0, default=20),
        "color": List(
            Number(only_integer=True, min_value=0, max_value=255),
            length=3,
            default=(0, 255, 0),
        ),
    }

    outputs = {"mask": Type(np.ndarray)}

    def process(self, image, **kwargs):
        mask = np.zeros(image.shape, np.uint8)

        global drawing
        drawing = False

        def paint_draw(event, x, y, flags, param):
            global ix, iy, drawing

            if event == cv2.EVENT_LBUTTONDOWN:
                drawing = True
            elif event == cv2.EVENT_LBUTTONUP:
                drawing = False
            elif event == cv2.EVENT_MOUSEMOVE and drawing:
                cv2.line(mask, (ix, iy), (x, y), kwargs["color"], kwargs["brush"])

            ix, iy = x, y

            return x, y

        cv2.namedWindow("image")
        cv2.setMouseCallback("image", paint_draw)

        while cv2.getWindowProperty("image", cv2.WND_PROP_VISIBLE) >= 1:
            cv2.imshow("image", cv2.addWeighted(image, 0.8, mask, 0.2, 0))
            key_code = cv2.waitKey(1)

            if (key_code & 0xFF) == ord("q"):
                cv2.destroyAllWindows()
                break
            elif (key_code & 0xFF) == ord("+"):
                kwargs["brush"] += 1
            elif (key_code & 0xFF) == ord("-") and kwargs["brush"] > 1:
                kwargs["brush"] -= 1

        mask = np.sum(mask, axis=2)
        mask[mask != 0] = 255

        return {"mask": mask}
