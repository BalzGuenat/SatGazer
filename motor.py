import gpiozero as gz
from gpiozero.pins.mock import MockFactory
from time import sleep

# the minimum time to wait between steps
STEP_TIME = .001

gz.Device.pin_factory = MockFactory()


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


if __name__ == "__main__":
    step_size = 360 / 512
    m0 = Motor(16, 17, step_size)
    m0.pos(90)
    m0.pos(90)
    m0.pos(180)
    m0.pos(90)
    m0.pos(359)
    m0.pos(0)
