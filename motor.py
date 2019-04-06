import gpiozero as gz
from gpiozero.pins.mock import MockFactory
from time import sleep
import abc

# the time to wait between steps
STEP_TIME = .002

gz.Device.pin_factory = MockFactory()


class Motor:
    """
    Base class for both bipolar and unipolar stepper motors.
    """
    def __init__(self, step_size):
        self.step_size = step_size

    def __str__(self):
        return "Motor"

    def degrees(self, deg):
        steps = int(deg / self.step_size)
        self.step(steps)

    def coast(self):
        """
        Lets the motor coast. Should be overridden by subclasses that support coasting.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def step(self, n=1):
        raise NotImplementedError


class BipolarMotor(Motor):
    """
    A bipolar motor, driven through a stepper motor driver
    using a step pin and a direction pin.
    """

    def __init__(self, step_pin, dir_pin, step_size):
        super().__init__(step_size)
        self.step_dev = gz.DigitalOutputDevice(step_pin)
        self.dir_dev = gz.DigitalOutputDevice(dir_pin)

    def __str__(self):
        return "BipolarMotor({},{})".format(self.step_dev.pin, self.dir_dev.pin)

    def step(self, n=1):
        if n < 0:
            n = -n
            reverse = True
        else:
            reverse = False
        print("stepping {} {}".format(n, "bwd" if reverse else "fwd"))
        self.dir_dev.value = reverse
        self.step_dev.blink(STEP_TIME, STEP_TIME, n, False)
        # for i in range(n):
        #     self.step_dev.toggle()
        #     sleep(STEP_TIME)

    def coast(self):
        raise Exception("Coasting not supported for this bipolar motor.")


class UnipolarMotor(Motor):
    def __init__(self, a0, a1, b0, b1, step_size, **kwargs):
        super().__init__(step_size)
        if "reverse" in kwargs and kwargs["reverse"]:
            a0, a1, b0, b1 = b1, b0, a1, a0
        self.a0 = gz.DigitalOutputDevice(a0)
        self.a1 = gz.DigitalOutputDevice(a1)
        self.b0 = gz.DigitalOutputDevice(b0)
        self.b1 = gz.DigitalOutputDevice(b1)
        self.phases = [[self.a0], [self.a1], [self.b0], [self.b1]]
        self.phase_idx = 0

    def __str__(self):
        return "UnipolarMotor({},{},{},{})".format(self.a0.pin, self.a1.pin, self.b0.pin, self.b1.pin)

    def step(self, n=1, step_time=STEP_TIME):
        if n < 0:
            n = -n
            reverse = True
        else:
            reverse = False
        print("{} stepping {} {}".format(self, n, "bwd" if reverse else "fwd"))
        phase_step = -1 if reverse else 1
        for i in range(n):
            [p.off() for p in self.phases[self.phase_idx]]
            self.phase_idx = (self.phase_idx + phase_step) % len(self.phases)
            [p.on() for p in self.phases[self.phase_idx]]
            sleep(step_time)

    def coast(self):
        [p.off() for p in self.phases[self.phase_idx]]
