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

from distutils.core import setup
from brother_pt import VERSION

setup(name='brother_pt',
      version=VERSION,
      description='Python package for the raster language protocol of the Brother PT series of connected label printers',
      author='Thomas Reidemeister',
      license='Apache 2.0',
      url='https://github.com/treideme/brother_pt',
      packages=['brother_pt'],
      install_requires=[
          'pyusb>=1.2.1',
          'Pillow==8.4.0',
          'packbits==0.6',
      ],
     )

