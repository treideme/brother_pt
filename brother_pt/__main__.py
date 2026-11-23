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

from brother_pt import VERSION
from .printer import *

TAPE_WIDTHS_MM = sorted(MediaWidthToTapeMargin.margin)


def show_status(serial):
    printers = find_printers(serial)
    if len(printers) == 0:
        print("No supported printers found, make sure the device is switched on", file=sys.stderr)
        return 1
    found_printer = BrotherPt(printers[0].serial_number)
    print("%s %s (%s):" % (printers[0].manufacturer, printers[0].product, printers[0].serial_number))
    print(" + Media width: %dmm" % found_printer.media_width)
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
            # No dimension matches the tape; scale the image to fit instead of
            # refusing it. See issue #4.
            original = (image.width, image.height)
            adjusted_image = fit_to_tape(image, found_printer.media_width)
            print('Scaled image from %ix%i to %ix%i to fit the %dpx tape height. '
                  'For barcodes/QR, render at %dpx height for the sharpest result.' %
                  (original[0], original[1], adjusted_image.width, adjusted_image.height,
                   required_height, required_height), file=sys.stderr)
    elif args.rotate == '0':
        adjusted_image = image
    elif args.rotate == '90':
        adjusted_image = image.rotate(90, expand=True)
    elif args.rotate == '180':
        adjusted_image = image.rotate(180, expand=True)
    elif args.rotate == '270':
        adjusted_image = image.rotate(270, expand=True)
    else:
        print('Invalid rotation specified: %s' % args.rotate, file=sys.stderr)
        return 1
    if adjusted_image.height != required_height:
        print('Height of output image does not match tape-width: (%i, %i) vs %i' %
              (adjusted_image.width, adjusted_image.height, required_height), file=sys.stderr)
        return 1

    image = select_raster_channel(adjusted_image, args.threshold)

    # Margin check
    margin = args.margin
    if (image.width + margin) < MINIMUM_TAPE_POINTS:
        print("Image (%i) + cut margin (%i) is smaller than minimum tape width (%i) ...\n"
              "cutting length will be extended" % (image.width, margin, MINIMUM_TAPE_POINTS))
        margin = MINIMUM_TAPE_POINTS - image.width

    # Raster image
    data = raster_image(image, found_printer.media_width)

    found_printer.print_data(data, margin, cut=not args.no_cut)

    return 0


def do_text(args):
    try:
        from .text import render_text_label
    except ImportError as exc:
        print('the text command needs the text extra: pip install "brother_pt[text]"\n(%s)' % exc,
              file=sys.stderr)
        return 1

    if args.tape_mm is not None:
        height = MediaWidthToTapeMargin.to_print_width(args.tape_mm)
        found_printer = None
    else:
        printers = find_printers(args.printer)
        if len(printers) == 0:
            print("No supported printers found, make sure the device is switched on", file=sys.stderr)
            return 1
        found_printer = BrotherPt(printers[0].serial_number)
        height = MediaWidthToTapeMargin.to_print_width(found_printer.media_width)

    try:
        image = render_text_label(
            args.text, height, font_path=args.font, font_size=args.size, spacing=args.spacing
        )
    except ValueError as exc:
        print("Cannot render text: %s" % exc, file=sys.stderr)
        return 1
    except OSError as exc:  # a bad --font path
        print("Could not load font %r: %s" % (args.font, exc), file=sys.stderr)
        return 1
    except ImportError as exc:  # a fontconfig pattern without the [fontconfig] extra
        print("Cannot render text: %s" % exc, file=sys.stderr)
        return 1

    if args.output:
        image.save(args.output)
        print("Wrote %s (%ix%i)" % (args.output, image.width, image.height))
        return 0

    if found_printer is None:
        print("--tape-mm renders without a printer; add --output FILE, or drop --tape-mm to print.",
              file=sys.stderr)
        return 1

    found_printer.print_image(image, margin_px=args.margin, cut=not args.no_cut)
    return 0


def _report_unsupported():
    """Print a hint for any recognised-but-unsupported printer that is attached."""
    for name, reason in find_unsupported_printers():
        print("Note: %s is connected but not supported -- %s" % (name, reason), file=sys.stderr)


def list_printers(serial):
    printers = find_printers(serial)
    if len(printers) == 0:
        print("No supported printers found, make sure the device is switched on", file=sys.stderr)
        _report_unsupported()
        return 1
    print("Discovered printers ...")
    print("      Vendor\tModel\t\tSerial")
    for i, found_printer in enumerate(printers):
        print(" (%2i) %s\t%s\t%s" %
              (i+1, found_printer.manufacturer, found_printer.product, found_printer.serial_number))
    _report_unsupported()

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
    print_menu = subparsers.add_parser('print')
    print_menu.add_argument("-r", "--rotate", default='auto',
                            choices=['auto', '0', '90', '180', '270'],
                            help='Rotate the image (counter clock-wise) by this amount of degrees. '
                                 '(default: %(default)s)')
    print_menu.add_argument("-t", "--threshold", type=float, default=None,
                            help="Threshold in percent (0-100): grayscale/colour pixels darker than this "
                                 "print as ink. Default: any pixel that is not pure white is ink.")
    print_menu.add_argument("-n", "--no-cut", action='store_true',
                            help="Don't cut the tape after printing the label.")
    print_menu.add_argument("-m", "--margin", type=int, default=0,
                            help="Print margin in dots.")
    print_menu.add_argument("-f", "--file", type=str, required=True, help="Image file to print")
    print_menu.set_defaults(cmd='print')

    text_menu = subparsers.add_parser('text', help='Print one or more lines of text')
    text_menu.add_argument("-f", "--font", type=str, default=None,
                           help="A .ttf/.otf font file path, or a fontconfig pattern "
                                "(e.g. 'Helsinki Narrow:style=Bold'). "
                                "Default: a stock sans-serif. For CJK pass a CJK font, "
                                "e.g. 'Noto Sans CJK JP'.")
    text_menu.add_argument("-s", "--size", type=int, default=None,
                           help="Font size in px (default: auto-fit the tape height).")
    text_menu.add_argument("--spacing", type=int, default=4, help="Pixels of gap between lines.")
    text_menu.add_argument("-m", "--margin", type=int, default=0, help="Print margin in dots.")
    text_menu.add_argument("-n", "--no-cut", action='store_true',
                           help="Don't cut the tape after printing the label.")
    text_menu.add_argument("--tape-mm", type=int, default=None, choices=TAPE_WIDTHS_MM,
                           help="Render for this tape width without querying a printer (use with --output).")
    text_menu.add_argument("-o", "--output", type=str, default=None,
                           help="Write the rendered label to this PNG instead of printing it.")
    text_menu.add_argument("text", nargs='+', help="Text to print; one argument per line.")
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
