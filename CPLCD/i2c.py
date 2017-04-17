# Copyright (C) 2013-2016 Danilo Bargen
# CircuitPython variant by Dan Halbert
# Copyright (C) 2017 Dan Halbert

# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
# the Software, and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
# FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
# IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import time

import busio
import board
from adafruit_bus_device.i2c_device import I2CDevice

from .lcd import BaseCharLCD, LCD_4BITMODE, LCD_BACKLIGHT, LCD_NOBACKLIGHT, PIN_ENABLE
from .lcd import MILLISECOND, MICROSECOND


class I2CLCD(BaseCharLCD):
    def __init__(self, address,
                       cols=20, rows=4, dotsize=8,
                       auto_linebreaks=True,
                       backlight_on=True):
        """
        CharLCD via PCF8574 I2C port expander.

        Pin mapping::

            7  | 6  | 5  | 4  | 3  | 2  | 1  | 0
            D7 | D6 | D5 | D4 | BL | EN | RW | RS

        :param address: The I2C address of your LCD.
        :type address: int
        :param cols: Number of columns per row (usually 16 or 20). Default: 20.
        :type cols: int
        :param rows: Number of display rows (usually 1, 2 or 4). Default: 4.
        :type rows: int
        :param dotsize: Some 1 line displays allow a font height of 10px.
            Allowed: 8 or 10. Default: 8.
        :type dotsize: int
        :param auto_linebreaks: Whether or not to automatically insert line breaks.
            Default: True.
        :type auto_linebreaks: bool
        :param backlight_on: Whether the backlight is turned on initially. Default: True.
        :type backlight_on: bool

        """
        # Set own address and port.
        self.address = address

        # Currently the I2C mode only supports 4 bit communication
        self.data_bus_mode = LCD_4BITMODE

        # Set backlight status now without sending it on.
        self._backlight_pin_state = LCD_BACKLIGHT if backlight_on else LCD_NOBACKLIGHT

        # Call superclass
        super().__init__(cols, rows, dotsize, auto_linebreaks=auto_linebreaks)

    def _init_connection(self):
        self.i2c = busio.I2C(board.SCL, board.SDA)
        self.i2c_device = I2CDevice(self.i2c, self.address)
        self.data_buffer = bytearray(1)
        self.data_byte = memoryview(self.data_buffer)[0]

    def _close_connection(self):
        self.i2c.deinit()

    @property
    def backlight_on(self):
        return self._backlight_pin_state == LCD_BACKLIGHT

    @backlight_on.setter
    def backlight_on(self, value):
        self._backlight_pin_state = LCD_BACKLIGHT if value else LCD_NOBACKLIGHT
        self._i2c_write(self._backlight_pin_state)

    # Low level commands

    def _send(self, value, rs_mode):
        """Send the specified value to the display in 4-bit nibbles.
        The rs_mode is either ``_RS_DATA`` or ``_RS_INSTRUCTION``."""
        self._write4bits(rs_mode | (value & 0xF0))
        self._write4bits(rs_mode | ((value << 4) & 0xF0))

    def _write4bits(self, value):
        """Write 4 bits of data into the data bus."""
        self._pulse_data(value | self._backlight_pin_state)

    def _write8bits(self, value):
        """Write 8 bits of data into the data bus."""
        raise NotImplementedError('I2C currently supports only 4bit.')

    def _pulse_data(self, value):
        """Pulse the `enable` flag to process value."""
        with self.i2c_device:
            self._i2c_write((value & ~PIN_ENABLE) | self._backlight_pin_state)
            time.sleep(MICROSECOND)
            self._i2c_write(value | PIN_ENABLE | self._backlight_pin_state)
            time.sleep(MICROSECOND)
            self._i2c_write((value & ~PIN_ENABLE) | self._backlight_pin_state)
        time.sleep(100*MICROSECOND)

    def _i2c_write(self, value):
        self.data_buffer[0] = value
        self.i2c_device.write(self.data_buffer)
