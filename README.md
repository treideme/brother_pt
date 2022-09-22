## brother_pt

Related [blog post](https://www.reidemeister.com/?p=544). This is work in progress...

A Python package to control Brother PT label printers. This library
implements the raster control set those printers and allows to 
configure these printers.

In particular, the following is supported:
 * Raster image files for direct printing
 * You can print image files directly from a Python script 
 * Supported backends
    * pyusb
    * Planned: linux kernel [usblp](https://github.com/torvalds/linux/blob/master/drivers/usb/class/usblp.c) backend
    * Planned: Bluetooth 

The following printers are supported by this package (✓ means verified by the author):
 * PT-P710BT (✓)
 * PT-E550W
 * PT-P750W 

Planned (not supported)
 * PT-P900
 * PT-P900W
 * PT-P950NW
 * PT-P910BT
 * PT-H500
 * PT-P700
 * PT-E500
 * PT-P300BT

## Background

Although Brother provides support for modern Linux versions for these 
printers, binary drivers are required. As such the supported platforms
are limited to desktop machines.

Further, the companion application does not seem to support direct
raster print (iPrint and Label). In particular the software scales
imported logos and image files with anti-aliasing when scaled, the
printer driver then tries to use dithering to approximate these
smooth edges resulting in poor print qualities of image files printed
by these tools. 
By accessing the raster command-set directly, though this module,
one can achieve higher print quality by exploiting the high resolution
print modes (180x180dpi so far supported) by these printers.

This package was inspired by [brother_ql](https://github.com/pklaus/brother_ql)
and [pt-p710bt-label-maker](https://github.com/robby-cornelissen/pt-p710bt-label-maker).
The former provided the architectural design queues for this module,
the latter provided a good initial reference for the command set used, though 
the provided functionality was severely limited.

The full documentation of the raster command set used by the above printers
can be found [here](http://www.brother.com/product/dev/index.htm).

## Installation

```bash
pip install --upgrade https://github.com/treideme/brother_pt/archive/master.zip
```

## Usage

The main user interface of this package is the command line tool `brother_pt`.
```
    Usage: brother_pt [OPTIONS] COMMAND [ARGS]...
    
      Command line interface for the brother_pt Python package.
    
    Options:
      -p, --printer <SN>              Serial number of a connected printer
      --debug
      --version                       Show the version and exit.
      --help                          Show this message and exit.
    
    Commands:
      discover  find connected label printers
      info      list available labels, models etc.
      print     Print a label
```

The global options are followed by a command such as `info` or `print`.
The most important command is the `print` command and here is its CLI signature:

    Usage: brother_pt print [OPTIONS] IMAGE [IMAGE] ...
    
      Print a label of the provided IMAGE.
    
    Options:
      -r, --rotate [auto|0|90|180|270]
                                      Rotate the image (counterclock-wise) by this
                                      amount of degrees.
      -t, --threshold FLOAT           The threshold value (in percent) to
                                      discriminate between black and white pixels.
      --no-cut                        Don't cut the tape after printing the label.
      --margin                        Print margin 
      --help                          Show this message and exit.

## Author

 * Thomas Reidemeister

## Contributing

There are many ways to support the development of brother_pt:

* **File an issue** on Github, if you encounter problems, have a proposal, etc.
* **Submit a pull request** on Github if you improved the code and know how to use git.
* **Finance a label printer** from the [author's wishlist](https://www.amazon.ca/hz/wishlist/ls/3R6ALF8DZQ0JY) to 
allow him to extend the device coverage and testing.