import math
from types import SimpleNamespace

import numpy as np

from pypulseq.opts import Opts


def make_trapezoid(
    channel: str,
    amplitude: float = 0,
    area: float = None,
    delay: float = 0,
    duration: float = 0,
    flat_area: float = 0,
    flat_time: float = -1,
    max_grad: float = 0,
    max_slew: float = 0,
    rise_time: float = 0,
    system: Opts = Opts(),
) -> SimpleNamespace:
    """
    Create a trapezoidal gradient event.

    See also:
    - `pypulseq.Sequence.sequence.Sequence.add_block()`
    - `pypulseq.opts.Opts`

    Parameters
    ----------
    channel : str
        Orientation of trapezoidal gradient event. Must be one of `x`, `y` or `z`.
    amplitude : float, default=0
        Amplitude.
    area : float, default=None
        Area.
    delay : float, default=0
        Delay in seconds (s).
    duration : float, default=0
        Duration in seconds (s).
    flat_area : float, default=0
        Flat area.
    flat_time : float, default=-1
        Flat duration in seconds (s). Default is -1 to account for triangular pulses.
    max_grad : float, default=0
        Maximum gradient strength.
    max_slew : float, default=0
        Maximum slew rate.
    rise_time : float, default=0
        Rise time in seconds (s).
    system : Opts, default=Opts()
        System limits.

    Returns
    -------
    grad : SimpleNamespace
        Trapezoidal gradient event created based on the supplied parameters.

    Raises
    ------
    ValueError
        If none of `area`, `flat_area` and `amplitude` are passed
        If requested area is too large for this gradient
        If `flat_time`, `duration` and `area` are not supplied.
        Amplitude violation
    """
    if channel not in ["x", "y", "z"]:
        raise ValueError(
            f"Invalid channel. Must be one of `x`, `y` or `z`. Passed: {channel}"
        )

    if max_grad <= 0:
        max_grad = system.max_grad

    if max_slew <= 0:
        max_slew = system.max_slew

    if rise_time <= 0:
        rise_time = system.rise_time

    if area is None and flat_area == 0 and amplitude == 0:
        raise ValueError("Must supply either 'area', 'flat_area' or 'amplitude'.")

    if flat_time != -1:
        if amplitude != 0:
            amplitude2 = amplitude
        elif (area is not None) and (rise_time > 0): # We have rise_time, flat_time and area.
            amplitude2 = area/(rise_time + flat_time)
        else:
            amplitude2 = flat_area / flat_time

        if rise_time == 0:
            rise_time = abs(amplitude2) / max_slew
            rise_time = (
                math.ceil(rise_time / system.grad_raster_time) * system.grad_raster_time
            )
        fall_time, flat_time = rise_time, flat_time
    elif duration > 0:
        amplitude2 = amplitude
        if amplitude == 0:
            if rise_time == 0:
                dC = 1 / abs(2 * max_slew) + 1 / abs(2 * max_slew)
                possible = duration**2 > 4 * abs(area) * dC
                amplitude2 = (
                    duration - math.sqrt(duration**2 - 4 * abs(area) * dC)
                ) / (2 * dC)
            else:
                amplitude2 = area / (duration - rise_time)
                possible = duration > 2 * rise_time and abs(amplitude2) < max_grad

            if not possible:
                raise ValueError("Requested area is too large for this gradient")

        if rise_time == 0:
            rise_time = (
                math.ceil(abs(amplitude2) / max_slew / system.grad_raster_time)
                * system.grad_raster_time
            )
            if rise_time == 0:
                rise_time = system.grad_raster_time

        fall_time = rise_time
        flat_time = duration - rise_time - fall_time

        if amplitude == 0:
            amplitude2 = area / (rise_time / 2 + fall_time / 2 + flat_time)
    else:
        if area == 0:
            raise ValueError("Must supply a duration.")
        else:
            rise_time = (
                math.ceil(math.sqrt(abs(area) / max_slew) / system.grad_raster_time)
                * system.grad_raster_time
            )
            amplitude2 = np.divide(area, rise_time)  # To handle nan
            t_eff = rise_time

            if abs(amplitude2) > max_grad:
                t_eff = (
                    math.ceil(abs(area) / max_grad / system.grad_raster_time)
                    * system.grad_raster_time
                )
                amplitude2 = area / t_eff
                rise_time = (
                    math.ceil(abs(amplitude2) / max_slew / system.grad_raster_time)
                    * system.grad_raster_time
                )

            flat_time = t_eff - rise_time
            fall_time = rise_time

    if abs(amplitude2) > max_grad:
        raise ValueError("Amplitude violation.")

    grad = SimpleNamespace()
    grad.type = "trap"
    grad.channel = channel
    grad.amplitude = amplitude2
    grad.rise_time = rise_time
    grad.flat_time = flat_time
    grad.fall_time = fall_time
    grad.area = amplitude2 * (flat_time + rise_time / 2 + fall_time / 2)
    grad.flat_area = amplitude2 * flat_time
    grad.delay = delay
    grad.first = 0
    grad.last = 0

    return grad
