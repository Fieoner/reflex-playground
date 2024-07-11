import multiprocessing
from multiprocessing.sharedctypes import SynchronizedArray
from multiprocessing.synchronize import Event

import libusb_package
import usb.core
import usb.backend.libusb1

from usb_info import HIDInfo


class USBDeviceList:
    """Device list class for a given dance pad specification."""

    @staticmethod
    def connected_device_names(info: HIDInfo) -> list[str | None]:
        devs: list[usb.core.Device] = []
        for dev in libusb_package.find(
            find_all=True,  idVendor=info.VID, idProduct=info.PID
        ):
            devs.append(dev)
        return [dev.serial_number for dev in devs]

    @staticmethod
    def get_device_by_serial(
        vid: int, pid: int, serial: str
    ) -> usb.core.Device | None:
        devices: list[usb.core.Device] | None = libusb_package.find(
            find_all=True, idVendor=vid, idProduct=pid
        )
        if devices is None:
            return
        for device in devices:
            if device.serial_number == serial:
                return device


class HIDEndpointProcess(multiprocessing.Process):
    """Base class that manages a single HID endpoint in its own process."""

    def __init__(self, pad_info: HIDInfo, serial: str, device: usb.core.Device, lock: multiprocessing.Lock):
        super(HIDEndpointProcess, self).__init__()
        self._info = pad_info
        self._serial = serial
        self._data = multiprocessing.Array('i', self._info.BYTES)
        self._event = multiprocessing.Event()
        self._device = device
        self._lock = lock
        self.start()

    def terminate(self) -> None:
        super().terminate()

    def run(self) -> None:
        while True:
            self._process()

    def _process(self) -> None:
        pass

    @property
    def data(self) -> SynchronizedArray:
        return self._data

    @property
    def event(self) -> Event:
        return self._event


class HIDReadProcess(HIDEndpointProcess):
    """Child class for reading data from an HID Endpoint."""

    def _process(self) -> None:
        print("reading")
        with self._lock:
            sensor_data = self._device.read(self._info.READ_EP, self._info.BYTES)
        with self._data.get_lock():
            for i, v in enumerate(sensor_data):
                self._data[i] = v
        self._event.set()


class HIDWriteProcess(HIDEndpointProcess):
    """Child class for writing data to an HID Endpoint."""

    def _process(self) -> None:
        print("writing")
        with self._data.get_lock():
            data = [d for d in self._data]
        with self._lock:
            self._device.write(self._info.WRITE_EP, data)
        self._event.set()
