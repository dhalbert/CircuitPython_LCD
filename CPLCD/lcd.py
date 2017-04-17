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
from micropython import const

# Commands
_LCD_CLEARDISPLAY = const(0x01)
_LCD_RETURNHOME = const(0x02)
_LCD_ENTRYMODESET = const(0x04)
_LCD_DISPLAYCONTROL = const(0x08)
_LCD_CURSORSHIFT = const(0x10)
_LCD_FUNCTIONSET = const(0x20)
_LCD_SETCGRAMADDR = const(0x40)
_LCD_SETDDRAMADDR = const(0x80)

# Flags for display entry mode
_LCD_ENTRYRIGHT = const(0x00)
_LCD_ENTRYLEFT = const(0x02)
_LCD_ENTRYSHIFTINCREMENT = const(0x01)
_LCD_ENTRYSHIFTDECREMENT = const(0x00)

# Flags for display on/off control
_LCD_DISPLAYON = const(0x04)
_LCD_DISPLAYOFF = const(0x00)
_LCD_CURSORON = const(0x02)
_LCD_CURSOROFF = const(0x00)
_LCD_BLINKON = const(0x01)
_LCD_BLINKOFF = const(0x00)

# Flags for display/cursor shift
_LCD_DISPLAYMOVE = const(0x08)
_LCD_CURSORMOVE = const(0x00)
_LCD_MOVERIGHT = const(0x04)
_LCD_MOVELEFT = const(0x00)

# Flags for function set
_LCD_8BITMODE = const(0x10)
LCD_4BITMODE = const(0x00)
_LCD_2LINE = const(0x08)
_LCD_1LINE = const(0x00)
_LCD_5x10DOTS = const(0x04)
_LCD_5x8DOTS = const(0x00)

# Flags for backlight control
LCD_BACKLIGHT = const(0x08)
LCD_NOBACKLIGHT = const(0x00)

# Flags for RS pin modes
_RS_INSTRUCTION = const(0x00)
_RS_DATA = const(0x01)

# Pin bitmasks
PIN_ENABLE = const(0x4)
PIN_READ_WRITE = const(0x2)
PIN_REGISTER_SELECT = const(0x1)

# Enums

class Alignment:
    LEFT = const(_LCD_ENTRYLEFT)
    RIGHT = const(_LCD_ENTRYRIGHT)

class ShiftMode:
    CURSOR = const(_LCD_ENTRYSHIFTDECREMENT)
    DISPLAY = const(_LCD_ENTRYSHIFTINCREMENT)

class CursorMode:
    HIDE = const(_LCD_CURSOROFF | _LCD_BLINKOFF)
    LINE = const(_LCD_CURSORON | _LCD_BLINKOFF)
    BLINK = const(_LCD_CURSOROFF | _LCD_BLINKON)

MICROSECOND = 1e-6
MILLISECOND = 1e-3

class BaseCharLCD(object):

    def __init__(self, cols=20, rows=4, dotsize=8, auto_linebreaks=True):
        """
        Character LCD controller. Base class only, you should use a subclass.

        Args:
            rows:
                Number of display rows (usually 1, 2 or 4). Default: 4.
            cols:
                Number of columns per row (usually 16 or 20). Default 20.
            dotsize:
                Some 1 line displays allow a font height of 10px.
                Allowed: 8 or 10. Default: 8.
            auto_linebreaks:
                Whether or not to automatically insert line breaks.
                Default: True.

        """
        if dotsize not in (8, 10):
            raise ValueError('The ``dotsize`` argument should be either 8 or 10.')
        self.dotsize = dotsize

        self.rows = rows
        self.cols = cols

        # get row addresses (varies based on display size)
        self.row_offsets = (0x00, 0x40, self.cols, 0x40 + self.cols)

        # Set up auto linebreaks
        self.auto_linebreaks = auto_linebreaks
        self.recent_auto_linebreak = False

        # Setup initial display configuration
        displayfunction = self.data_bus_mode | _LCD_5x8DOTS
        if self.rows == 1:
            displayfunction |= _LCD_1LINE
        elif self.rows in (2, 4):
            # LCD only uses two lines on 4 row displays
            displayfunction |= _LCD_2LINE
        if self.dotsize == 10:
            # For some 1 line displays you can select a 10px font.
            displayfunction |= _LCD_5x10DOTS

        # Initialize display
        self._init_connection()

        # Choose 4 or 8 bit mode
        if self.data_bus_mode == LCD_4BITMODE:
            # Hitachi manual page 46
            self.command(0x03)
            time.sleep(4.5*MILLISECOND)
            self.command(0x03)
            time.sleep(4.5*MILLISECOND)
            self.command(0x03)
            time.sleep(100*MICROSECOND)
            self.command(0x02)
        elif self.data_bus_mode == _LCD_8BITMODE:
            # Hitachi manual page 45
            self.command(0x30)
            time.sleep(4.5*MILLISECOND)
            self.command(0x30)
            time.sleep(100*MICROSECOND)
            self.command(0x30)
        else:
            raise ValueError('Invalid data bus mode: {}'.format(self.data_bus_mode))

        # Write configuration to display
        self.command(_LCD_FUNCTIONSET | displayfunction)
        time.sleep(50*MICROSECOND)

        # Configure display mode
        self._display_mode = _LCD_DISPLAYON
        self._cursor_mode = int(CursorMode.HIDE)
        self.command(_LCD_DISPLAYCONTROL | self._display_mode | self._cursor_mode)
        time.sleep(50*MICROSECOND)

        # Clear display
        self.clear()

        # Configure entry mode
        self._text_align_mode = int(Alignment.LEFT)
        self._display_shift_mode = int(ShiftMode.CURSOR)
        self._cursor_pos = (0, 0)
        self.command(_LCD_ENTRYMODESET | self._text_align_mode | self._display_shift_mode)
        time.sleep(50*MICROSECOND)

    def close(self, clear=False):
        if clear:
            self.clear()
        self._close_connection()

    # Properties
    @property
    def cursor_pos(self):
        """The cursor position as a 2-tuple (row, col)."""
        return self._cursor_pos

    @cursor_pos.setter
    def cursor_pos(self, value):
        if len(value) != 2:
            raise ValueError('Cursor position should be determined by a 2-tuple.')
        if not (0 <= value[0] < self.rows) or not (0 <= value[1] < self.cols):
            raise ValueError('Cursor position {pos!r} invalid on a {lcd.rows}x{lcd.cols} LCD.'.format(pos=value, lcd=self))
        self._cursor_pos = value
        self.command(_LCD_SETDDRAMADDR | self.row_offsets[value[0]] + value[1])
        time.sleep(50*MICROSECOND)

    @property
    def text_align_mode(self):
        """The text alignment (``Alignment.LEFT`` or ``Alignment.RIGHT``)."""
        return self._text_align_mode

    @text_align_mode.setter
    def text_align_mode(self, value):
        self._text_align_mode = value
        self.command(_LCD_ENTRYMODESET | self._text_align_mode | self._display_shift_mode)
        time.sleep(50*MICROSECOND)

    @property
    def write_shift_mode(self):
        """The shift mode when writing (``ShiftMode.CURSOR`` or ``ShiftMode.DISPLAY``)."""
        return self._display_shift_mode

    @write_shift_mode.setter
    def write_shift_mode(self, value):
        self._display_shift_mode = value
        self.command(_LCD_ENTRYMODESET | self._text_align_mode | self._display_shift_mode)
        time.sleep(50*MICROSECOND)

    @property
    def display_enabled(self):
        """Whether or not to display any characters."""
        return self._display_mode == _LCD_DISPLAYON

    @display_enabled.setter
    def display_enabled(self, value):
        self._display_mode = _LCD_DISPLAYON if value else _LCD_DISPLAYOFF
        self.command(_LCD_DISPLAYCONTROL | self._display_mode | self._cursor_mode)
        time.sleep(50*MICROSECOND)

    @property
    def cursor_mode(self):
        """How the cursor should behave (``CursorMode.HIDE``, ``CursorMode.LINE`` or ``CursorMode.BLINK``."""
        return self._cursor_mode

    @cursor_mode.setter
    def cursor_mode(self, value):
        self._cursor_mode = value
        self.command(_LCD_DISPLAYCONTROL | self._display_mode | self._cursor_mode)
        time.sleep(50*MICROSECOND)

    # High level commands

    def print(self, value):
        """
        Write the specified unicode string to the display.

        To control multiline behavior, use newline (``\\n``) and carriage
        return (``\\r``) characters.

        Lines that are too long automatically continue on next line, as long as
        ``auto_linebreaks`` has not been disabled.

        Only characters with an ``ord()`` value between 0 and 255 are currently
        supported.

        """
        ignored = None  # Used for ignoring manual linebreaks after auto linebreaks
        for char in value:
            # Write regular chars
            if char not in '\n\r':
                self.write(ord(char))
                ignored = None
                continue
            # If an auto linebreak happened recently, ignore this write.
            if self.recent_auto_linebreak is True:
                # No newline chars have been ignored yet. Do it this time.
                if ignored is None:
                    ignored = char
                    continue
                # A newline character has been ignored recently. If the current
                # character is different, ignore it again. Otherwise, reset the
                # ignored character tracking.
                if ignored != char:  # A carriage return and a newline
                    ignored = None  # Reset ignore list
                    continue
            # Handle newlines and carriage returns
            row, col = self.cursor_pos
            if char == '\n':
                if row < self.rows - 1:
                    self.cursor_pos = (row + 1, col)
                else:
                    self.cursor_pos = (0, col)
            elif char == '\r':
                if self.text_align_mode == Alignment.LEFT:
                    self.cursor_pos = (row, 0)
                else:
                    self.cursor_pos = (row, self.cols - 1)

    def clear(self):
        """Overwrite display with blank characters and reset cursor position."""
        self.command(_LCD_CLEARDISPLAY)
        self._cursor_pos = (0, 0)
        self._content = [[0x20] * self.cols for _ in range(self.rows)]
        time.sleep(2*MILLISECOND)

    def home(self):
        """Set cursor to initial position and reset any shifting."""
        self.command(_LCD_RETURNHOME)
        self._cursor_pos = (0, 0)
        time.sleep(2*MILLISECOND)

    def shift_display(self, amount):
        """Shift the display. Use negative amounts to shift left and positive
        amounts to shift right."""
        if amount == 0:
            return
        direction = _LCD_MOVERIGHT if amount > 0 else _LCD_MOVELEFT
        for i in range(abs(amount)):
            self.command(_LCD_CURSORSHIFT | _LCD_DISPLAYMOVE | direction)
            time.sleep(50*MICROSECOND)

    def create_char(self, location, bitmap):
        """Create a new character.

        The HD44780 supports up to 8 custom characters (location 0-7).

        :param location: The place in memory where the character is stored.
            Values need to be integers between 0 and 7.
        :type location: int
        :param bitmap: The bitmap containing the character. This should be a
            bytearray of 8 numbers, each representing a 5 pixel row.
        :type bitmap: bytearray
        :raises AssertionError: Raised when an invalid location is passed in or
            when bitmap has an incorrect size.

        Example:

        .. sourcecode:: python

            >>> smiley = bytearray(
            ...     0b00000,
            ...     0b01010,
            ...     0b01010,
            ...     0b00000,
            ...     0b10001,
            ...     0b10001,
            ...     0b01110,
            ...     0b00000,
            ... )
            >>> lcd.create_char(0, smiley)

        """
        if not (0 <= location <= 7):
            raise ValueError('Only locations 0-7 are valid.')
        if len(bitmap) != 8:
            raise ValueError('Bitmap should have exactly 8 rows.')

        # Store previous position
        pos = self.cursor_pos

        # Write character to CGRAM
        self.command(_LCD_SETCGRAMADDR | location << 3)
        for row in bitmap:
            self._send(row, _RS_DATA)

        # Restore cursor pos
        self.cursor_pos = pos

    # Mid level commands

    def command(self, value):
        """Send a raw command to the LCD."""
        self._send(value, _RS_INSTRUCTION)

    def write(self, value):
        """Write a raw character byte to the LCD."""

        # Get current position
        row, col = self._cursor_pos
        self._send(value, _RS_DATA)

        # Update cursor position.
        if self.text_align_mode == Alignment.LEFT:
            if self.auto_linebreaks is False or col < self.cols - 1:
                # No newline, update internal pointer
                newpos = (row, col + 1)
                self._cursor_pos = newpos
                self.recent_auto_linebreak = False
            else:
                # Newline, reset pointer
                if row < self.rows - 1:
                    self.cursor_pos = (row + 1, 0)
                else:
                    self.cursor_pos = (0, 0)
                self.recent_auto_linebreak = True
        else:
            if self.auto_linebreaks is False or col > 0:
                # No newline, update internal pointer
                newpos = (row, col - 1)
                self._cursor_pos = newpos
                self.recent_auto_linebreak = False
            else:
                # Newline, reset pointer
                if row < self.rows - 1:
                    self.cursor_pos = (row + 1, self.cols - 1)
                else:
                    self.cursor_pos = (0, self.cols - 1)
                self.recent_auto_linebreak = True
