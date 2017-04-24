Introduction
============

CircuitPython library for HD77480 LCD character displays with an I2C backpack.
Currently PCF8574 is supported.

The original code started with the RPLCD library by Danilo Bargen, in https://github.com/dbrgn/RPLCD,
but it has been reworked considerably.

``lcd/lcd.py`` is too big to use as ``.py``. Use ``mpy-cross`` to convert the ``.py`` files into ``.mpy``.

Usage Example
=============

The ``LCD`` supports character LCDs using the HD77480 chip.

The interface to the LCD is separated into an ``Interface`` class.
Currently there is only one such class: ``I2CPCF8574Interface``.

.. code-block:: python

    from lcd.lcd import LCD
    from lcd.i2c_pcf8574_interface import I2CPCF8574Interface

    from lcd.lcd import CursorMode

    # Talk to the LCD at I2C address 0x27.
    # The number of rows and columns defaults to 4x20, so those
    # arguments could be omitted in this case.
    lcd = LCD(I2CPCF8574Interface(0x27), num_rows=4, num_cols=20)

    lcd.print("abc ")
    lcd.print("This is quite long and will wrap onto the next line automatically.")

    lcd.clear()

    # Start at the second line, fifth column (numbering from zero).
    lcd.set_cursor_pos(1, 4)
    lcd.print("Here I am")

    # Make the cursor visible as a line.
    lcd.set_cursor_mode(CursorMode.LINE)
