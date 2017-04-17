# CircuitPython_LCD
CircuitPython library for HD77480 displays with an I2C backpack (PCF8574 initially)

This is a considerably reworked version of the RPLCD library by Danilo Bargen,
in https://github.com/dbrgn/RPLCD. It has been adapted for use in CircuitPython,
which does I2C differently. Python 2 compatibility has been removed, and 
uses of features of Python 3 not in CircuitPython were also removed. A number
of changes were made for efficiency and clarity.

