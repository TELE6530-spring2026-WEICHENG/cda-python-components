#####
#
# Shared access layer for Raspberry Pi hardware peripherals used by CDA
# embedded adapter tasks.
#
# Heavy imports (board / busio / gpiozero / adafruit drivers) are kept
# inside the helper functions so a non-Pi dev machine can still import
# the adapter tasks for unit testing without installing RPi-only
# packages.
#

import logging
import threading

import programmingtheiot.common.ConfigConst as ConfigConst
from programmingtheiot.common.ConfigUtil import ConfigUtil


_lock = threading.RLock()

_i2cBus = None
_ads1115Cache = {}
_aht20Cache = {}
_outputDeviceCache = {}


def _getConfigInt(key: str, default: int) -> int:
    raw = ConfigUtil().getProperty(
        section=ConfigConst.CONSTRAINED_DEVICE, key=key, defaultVal=None,
    )
    if raw is None or raw == ConfigConst.NOT_SET:
        return default
    try:
        return int(str(raw).strip(), 0)
    except ValueError:
        logging.warning("Invalid integer config for %s=%r; using default %s.", key, raw, default)
        return default


def get_i2c_bus():
    """Return a cached busio.I2C instance."""
    global _i2cBus
    with _lock:
        if _i2cBus is None:
            import board
            import busio
            _i2cBus = busio.I2C(board.SCL, board.SDA)
            logging.info("Initialized I2C bus via busio.I2C().")
        return _i2cBus


def get_ads1115(addr: int = None):
    """Return a cached ADS1115 instance for the given I2C address."""
    if addr is None:
        addr = _getConfigInt(ConfigConst.ADS1115_I2C_ADDR_KEY, 0x48)
    with _lock:
        if addr in _ads1115Cache:
            return _ads1115Cache[addr]
        from adafruit_ads1x15.ads1115 import ADS1115
        ads = ADS1115(get_i2c_bus(), address=addr)
        _ads1115Cache[addr] = ads
        logging.info("Initialized ADS1115 at 0x%02X.", addr)
        return ads


def get_ads1115_channel(channel: int, addr: int = None):
    """Return an AnalogIn wrapper for the requested single-ended channel."""
    from adafruit_ads1x15.analog_in import AnalogIn
    if channel not in (0, 1, 2, 3):
        raise ValueError("ADS1115 channel must be 0-3, got %s" % channel)
    return AnalogIn(get_ads1115(addr), channel)


def get_aht20(addr: int = None):
    """Return a cached AHT20 sensor instance (shared by humidity + temp tasks)."""
    if addr is None:
        addr = _getConfigInt(ConfigConst.AHT_I2C_ADDR_KEY, 0x38)
    with _lock:
        if addr in _aht20Cache:
            return _aht20Cache[addr]
        import adafruit_ahtx0
        aht = adafruit_ahtx0.AHTx0(get_i2c_bus(), address=addr)
        _aht20Cache[addr] = aht
        logging.info("Initialized AHT20 at 0x%02X.", addr)
        return aht


def get_output_device(pin: int, active_high: bool = False, initial_value: bool = False):
    """Return a cached gpiozero.DigitalOutputDevice for the given BCM pin."""
    with _lock:
        if pin in _outputDeviceCache:
            return _outputDeviceCache[pin]
        from gpiozero import DigitalOutputDevice
        dev = DigitalOutputDevice(
            pin, active_high=active_high, initial_value=initial_value,
        )
        _outputDeviceCache[pin] = dev
        logging.info(
            "Initialized gpiozero output on BCM pin %d (active_high=%s).",
            pin, active_high,
        )
        return dev


def release_output_device(pin: int):
    """Close and drop a cached output device."""
    with _lock:
        dev = _outputDeviceCache.pop(pin, None)
    if dev is not None:
        try:
            dev.close()
        except Exception:
            logging.warning("Failed to close output device on pin %d.", pin, exc_info=True)


def reset_for_test():
    """Clear all cached hardware handles. Test-only hook."""
    global _i2cBus
    with _lock:
        _i2cBus = None
        _ads1115Cache.clear()
        _aht20Cache.clear()
        for dev in list(_outputDeviceCache.values()):
            try:
                dev.close()
            except Exception:
                pass
        _outputDeviceCache.clear()
