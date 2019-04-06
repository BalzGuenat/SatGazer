import gpiozero as gz
from gpiozero.pins.mock import MockFactory
from time import sleep

# the minimum time to wait between steps
STEP_TIME = .002

# gz.Device.pin_factory = MockFactory()


class Motor:
    def __init__(self, step_pin, dir_pin, step_size):
        self.step_dev = gz.DigitalOutputDevice(step_pin)
        self.dir_dev = gz.DigitalOutputDevice(dir_pin)
        self.step_size = step_size
        self.position = 0

    def __str__(self):
        return "Motor({},{})@{}".format(self.step_dev.pin, self.dir_dev.pin, self.position)

    def calibrate(self):
        self.position = 0

    def pos(self, pos, sync=True):
        diff = (pos - self.position) % 360
        if diff > 180:
            diff = diff - 360
        self.degrees(0, diff, sync)

    def degrees(self, direction, deg, sync=False):
        steps = int(deg / self.step_size)
        self.step(direction, steps, sync)

    def step(self, direction, n=1, sync=False):
        if n < 0:
            n = -n
            direction = not direction
        print("stepping {} {}".format(n, "bwd" if direction else "fwd"))
        self.dir_dev.value = direction
        self.step_dev.blink(STEP_TIME, STEP_TIME, n, not sync)
        # for i in range(n):
        #     self.step_dev.toggle()
        #     sleep(STEP_TIME)
        self.position = (self.position + n * self.step_size * (-1 if direction else 1)) % 360
        # print("now at {}".format(self.position))


class UnipolarMotor(Motor):
    def __init__(self, a0, a1, b0, b1, step_size):
        self.a0 = gz.DigitalOutputDevice(a0)
        self.a1 = gz.DigitalOutputDevice(a1)
        self.b0 = gz.DigitalOutputDevice(b0)
        self.b1 = gz.DigitalOutputDevice(b1)
        self.phases = [[self.a0], [self.a1], [self.b0], [self.b1]]
        self.step_size = step_size
        self.position = 0
        self.phase_idx = 0
    def step(self, direction, n=1, sync=True, step_time=STEP_TIME):
        if n < 0:
            n = -n
            direction = not direction
        # print("stepping {} {}".format(n, "bwd" if direction else "fwd"))
        for i in range(n):
            [p.off() for p in self.phases[self.phase_idx]]
            self.phase_idx = (self.phase_idx + (-1 if direction else 1)) % len(self.phases)
            [p.on() for p in self.phases[self.phase_idx]]
            sleep(step_time)
        self.position = (self.position + n * self.step_size * (-1 if direction else 1)) % 360
        # print("now at {}".format(self.position))
    def coast(self):
        [p.off() for p in self.phases[self.phase_idx]]


# from motor import UnipolarMotor
# blue, purple, yellow, orange
m = UnipolarMotor(18, 17, 22, 23, 5.625/128)


if __name__ == "__main__":
    step_size = 360 / 512
    m0 = Motor(16, 17, step_size)
    m0.pos(90)
    m0.pos(90)
    m0.pos(180)
    m0.pos(90)
    m0.pos(359)
    m0.pos(0)
