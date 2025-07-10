"""
   Copyright 2022 Thomas Reidemeister

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""
import argparse

import PIL.ImageOps

from brother_pt import VERSION
from .printer import *
from .cmd import *
from .font import *

def show_status(serial):
    printers = find_printers(serial)
    if len(printers) == 0:
        print("No supported printers found, make sure the device is switched on", file=sys.stderr)
        return 1
    found_printer = BrotherPt(printers[0].serial_number)
    print("%s %s (%s):" % (printers[0].manufacturer, printers[0].product, printers[0].serial_number))
    print(" + Media width: %dmm" % found_printer.media_width)
    print("                (%dpx)" % MediaWidthToTapeMargin.to_print_width(found_printer.media_width))
    print(" + Media type : %s" % found_printer.media_type.name)
    print(" + Tape color : %s" % found_printer.tape_color.name)
    print(" + Text color : %s" % found_printer.text_color.name)
    print()
    return 0


def do_print(args):
    printers = find_printers(args.printer)
    if len(printers) == 0:
        print("No supported printers found, make sure the device is switched on", file=sys.stderr)
        return 1

    found_printer = BrotherPt(printers[0].serial_number)

    image = Image.open(args.file)
    required_height = MediaWidthToTapeMargin.to_print_width(found_printer.media_width)

    # Apply rotation as specified
    if args.rotate == 'auto':
        adjusted_image = make_fit(image, found_printer.media_width)
        if adjusted_image is None:
            print('Could not auto-rotate image, at least one dimension needs to match the tape width (%i, %i) vs %i',
                  (image.width, image.height, required_height), file=sys.stderr)
            return 1
    elif args.rotate == '0':
        adjusted_image = image
    elif args.rotate == '90':
        adjusted_image = image.rotate(90, expand=True)
    elif args.rotate == '180':
        adjusted_image = image.rotate(180, expand=True)
    elif args.rotate == '270':
        adjusted_image = image.rotate(270, expand=True)
    else:
        print('Invalid rotation specified %s', file=sys.stderr)
        return 1
    if adjusted_image.height != required_height:
        print('Height of output image does not match tape-width (%i, %i) vs %i',
              (adjusted_image.width, adjusted_image.height, required_height), file=sys.stderr)
        return 1

    image = select_raster_channel(adjusted_image)

    # Margin check
    margin = args.margin
    if (image.width + margin) < MINIMUM_TAPE_POINTS:
        print("Image (%i) + cut margin (%i) is smaller than minimum tape width (%i) ...\n"
              "cutting length will be extended" % (image.width, margin, MINIMUM_TAPE_POINTS))
        margin = MINIMUM_TAPE_POINTS - image.width

    # Raster image
    data = raster_image(image, found_printer.media_width)

    found_printer.print_data(data, margin)

    return 0


def do_text(args):
    printers = find_printers(args.printer)
    if len(printers) == 0:
        print("No supported printers found, make sure the device is switched on", file=sys.stderr)
        return 1

    found_printer = BrotherPt(printers[0].serial_number)
    required_height = MediaWidthToTapeMargin.to_print_width(found_printer.media_width)
    
    FONT_DEFAULTS = [
        ( "Helsinki Narrow:style=Bold", 40, 6 ),
        ( "Helsinki", 22, 8 ),
        ( "Helsinki", 22, 4 ),
    ]
    baseline_spacing = 4
    
    fontpattern = args.font
    fontsize = args.size
    if args.font and args.font.isdigit():
        # The font is a number -- so we choose it as an index into
        # FONT_DEFAULTS.
        fontpattern, fontsize, baseline_spacing = FONT_DEFAULTS[int(args.font)]
        font = Font(pattern = fontpattern, size = fontsize)
        totheight = 0
        for t in args.text:
            if totheight:
                totheight += baseline_spacing
            w,h,baseline = font.text_dimensions(t)
            totheight += h
        if totheight > required_height:
            print(f"text does not fit on label with font {args.font} -- total height is {totheight} px, but label is {required_height} px!")
            return 1
    elif not fontpattern or not fontsize:
        # Try to pick some sensible defaults.
        nlines = 1
        print(f"{nlines} lines on media size {required_height} px")
        for fontpattern, fontsize, baseline_spacing in FONT_DEFAULTS:
            font = Font(pattern = fontpattern, size = fontsize)
            totheight = 0
            for t in args.text:
                if totheight:
                    totheight += baseline_spacing
                w,h,baseline = font.text_dimensions(t)
                totheight += h
            print(f"{fontpattern} @ {fontsize} is {totheight} px")
            if totheight <= required_height:
                print("that fits, good enough for me")
                break
    else:
        font = Font(pattern = fontpattern, size = fontsize)
    image = font.render_texts(args.text, height = required_height, vcenter = True, hcenter = False, spacing = baseline_spacing).pixels

    # Margin check
    margin = args.margin
    if (image.width + margin) < MINIMUM_TAPE_POINTS:
        print("Image (%i) + cut margin (%i) is smaller than minimum tape width (%i) ...\n"
              "cutting length will be extended" % (image.width, margin, MINIMUM_TAPE_POINTS))
        margin = MINIMUM_TAPE_POINTS - image.width

    if args.preview:
        w,h = image.size
        im2 = Image.new('L', (w + margin * 2, h), 0)
        im2.paste(image, (margin, 0))
        PIL.ImageOps.invert(im2).show()
        return

    # Raster image
    data = raster_image(image, found_printer.media_width)

    found_printer.print_data(data, margin)

    return 0


def list_printers(serial):
    printers = find_printers(serial)
    if len(printers) == 0:
        print("No supported printers found, make sure the device is switched on", file=sys.stderr)
        return 1
    print("Discovered printers ...")
    print("      Vendor\tModel\t\tSerial")
    for i, found_printer in enumerate(printers):
        print(" (%2i) %s\t%s\t%s" %
              (i+1, found_printer.manufacturer, found_printer.product, found_printer.serial_number))

    return 0


def cli():
    parser = argparse.ArgumentParser(prog='brother_pt',
                                     description='Command line interface for the brother_pt Python package.',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    # Parameters for actual flashing
    parser.add_argument("-p", "--printer", action='store', default=None, help="Serial number of a connected printer")
    parser.add_argument("-d", "--debug", action='store_true', help="Debugging output")
    parser.add_argument("-v", "--version", action='store_true', help="Show the version and exit.")

    # subparsers for commands
    subparsers = parser.add_subparsers(help="Commands:")

    # Atomic sub-parsers
    discover = subparsers.add_parser('discover', help='Discover supported printers')
    discover.set_defaults(cmd='discover')

    discover = subparsers.add_parser('info', help='List information about a connected printer')
    discover.set_defaults(cmd='info')

    # Complex subparsers
    print_menu = subparsers.add_parser('print', help="Print an image")
    print_menu.add_argument("-r", "--rotate", default='auto',
                            choices=['auto', '0', '90', '180', '270'],
                            help='Rotate the image (counter clock-wise) by this amount of degrees. '
                                 '(default: %(default)s)')
    #print_menu.add_argument("-t", "--threshold", type=float, default=0.1,
    #                        help="The threshold value (in percent) to discriminate between black and white pixels.")
    #print_menu.add_argument("-n", "--no-cut", action='store_true', help="Don't cut the tape after printing the label.")
    print_menu.add_argument("-m", "--margin", type=int, default=0,
                            help="Print margin in dots.")
    print_menu.add_argument("-f", "--file", type=str, required=True, help="Image file to print")
    print_menu.set_defaults(cmd='print')

    text_menu = subparsers.add_parser('text', help="Print some text")
    text_menu.add_argument("-m", "--margin", type=int, default=50,
                           help="Print margin in dots.")
    text_menu.add_argument("-f", "--font", type=str, default=None, help="Font face, or a number specifying an index into the default table of fonts")
    text_menu.add_argument("-s", "--size", type=int, default=None, help="Font size")
    text_menu.add_argument("--preview", action='store_true', help="just show a preview, don't print a label")
    text_menu.add_argument("text", nargs='+', help="Text to print")
    text_menu.set_defaults(cmd='text')

    args = parser.parse_args()

    if args.version:
        print(VERSION)
        return 0

    if args.debug:
        show_status(args.printer)

    elif 'cmd' not in args:
        print('Missing command', file=sys.stderr)
        parser.print_help()
        return 1
    elif args.cmd == 'discover':
        return list_printers(args.printer)
    elif args.cmd == 'info':
        if not args.debug:
            return show_status(args.printer)
        else:
            return 0
    elif args.cmd == 'print':
        return do_print(args)
    elif args.cmd == 'text':
        return do_text(args)

    return 0


if __name__ == '__main__':
    sys.exit(cli())
