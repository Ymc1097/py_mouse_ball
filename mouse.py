# -*- coding: utf-8 -*-
"""
Created on Tue Sep  6 14:17:40 2022

@author: Administrator
"""

import usb


def decode_G102(raw_data):
    dx = raw_data[2] if raw_data[3] == 0 else raw_data[2] - 256
    dy = -raw_data[4] if raw_data[5] == 0 else 256 - raw_data[4]
    return dx, dy


def decode_M500(raw_data):
    raw_x = (raw_data[2] & 15) << 8 | raw_data[1]
    raw_y = (raw_data[2] >> 4) | (raw_data[3] << 4)
    dx = raw_x if raw_x & 2048 == 0 else raw_x - 4096
    dy = -raw_y if raw_y & 2048 == 0 else 4096 - raw_y
    return dx, dy


supported_mouses = {
    '': {},
    'Logitech G102 2': {'vid': 0x046D, 'pid': 0xC09D, 'ep': 0x81, 'buffer': 8, 'decode_function': decode_G102},
    'Logitech M500': {'vid': 0x046D, 'pid': 0xC069, 'ep': 0x81, 'buffer': 6, 'decode_function': decode_M500},
}


class Mouse:
    dev_iter = None

    @classmethod
    def reset(cls):
        cls.dev_iter = None

    def __init__(self, mouse_type: str):
        if mouse_type not in supported_mouses.keys():
            raise NotImplementedError('This kind of mouse is not supported')
        vid = supported_mouses[mouse_type]['vid']
        pid = supported_mouses[mouse_type]['pid']
        self.ep = supported_mouses[mouse_type]['ep']
        self.buffer = supported_mouses[mouse_type]['buffer']
        self.decode_function = supported_mouses[mouse_type]['decode_function']

        if Mouse.dev_iter is None:
            Mouse.dev_iter = usb.core.find(idVendor=vid, idProduct=pid, find_all=True)
            self.dev = next(Mouse.dev_iter)
        else:
            self.dev = next(Mouse.dev_iter)
            self.dev = next(Mouse.dev_iter)

        self.X = 0
        self.Y = 0

    def update(self, verbose=False):
        while True:
            try:
                raw_data = self.dev.read(self.ep, self.buffer)
                # print(raw_data)
                dx, dy = self.decode_function(raw_data)
                self.X += dx
                self.Y += dy
                if verbose:
                    print(f'X:{self.X}, Y:{self.Y}')

            except usb.core.USBError:
                continue

    def clear(self):
        self.X = 0
        self.Y = 0
