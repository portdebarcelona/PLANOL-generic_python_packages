#  coding=utf-8
#
#  Author: Ernesto Arredondo Martinez (ernestone@gmail.com)
#  Created: 7/6/19 18:23
#  Last modified: 7/6/19 18:21
#  Copyright (c) 2019

# Convert a file png in a SVG file

import base64
import os

from PIL import Image


def png2svg(path_png, w_svg=None, h_svg=None, w_png=None, h_png=None, centre_x_png=0, centre_y_png=0):
    svg_string = """<?xml version="1.0" encoding="UTF-8" standalone="no"?>
    <!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">
    <svg version="1.1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"
    width="{w_svg}mm" height="{h_svg}mm" viewBox="0 0 {w_svg} {h_svg}">
    <image xlink:href="data:image/png;base64,{base64png}" width="{w_png}" height="{h_png}" x="{centre_x_png}" y="{centre_y_png}" />
    </svg>
    """

    with open(path_png, 'rb') as pngFile:
        base64String = base64.b64encode(pngFile.read()).decode("ascii")

    path_svg = os.path.splitext(path_png)[0]+".svg"

    with open(path_svg,'w') as svgFile:
        if not w_png:
            with Image.open(path_png) as img:
                w_png, h_png = img.size

        if not w_svg:
            w_svg = str(w_png) + "px"
            h_svg = str(h_png) + "px"

        svgFile.write(svg_string.format(w_svg=w_svg,
                                        h_svg=h_svg,
                                        w_png=w_png,
                                        h_png=h_png,
                                        centre_x_png=centre_x_png,
                                        centre_y_png=centre_y_png,
                                        base64png=base64String))

    print('Converted '+ path_png + ' to ' + path_svg)


if __name__ == '__main__':
    import fire
    fire.Fire()
