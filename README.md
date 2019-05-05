# SatGazer

SatGazer is a device that tracks a satellite and points an arrow at it.
It does this using a Raspberry Pi Zero, a pair of cheap stepper motors with matching driver boards and some 3D-printed parts.

## Inspiration

I had read that you could see the International Space Station with the naked eye if you knew where and when to look.
I tried this once when an overhead pass at my location was scheduled but couldn't find the tiny satellite in the large night sky.
I wanted someone or something to point out roughly the direction I had to look.
Then, a coworker mentioned a device used in Astro-Photography that cancelled out Earth's rotation for the purpose o long-exposure photographs of the night sky.
This gave me the initial idea for SatGazer.
I also wanted to finally learn how stepper motors are controlled and recently got a 3D printer, so I got to work.

## Basic Idea of the Design

To be able to point in any direction, the device uses two axes.

When starting SatGazer, two threads are running.
The main thread becomes the web server thread that waits for incomming requests and commands.

The tracking of the satellite runs in its own thread that periodically (once per second) realigns the SatGazer arrow to point towards the satellite.
It also fetches new future positions of the satellite when necessary.

### Satellite Location and 3D Math

(Implemented in satpoint.py)

The satellite location is fetched from a web API, currently n2yo.com.
With one request, the locations for the next N seconds can be obtained.
This means that SatGazer doesn't have to request new positions for every update but only when it runs out of previously fetched locations or when the target satellite changes.

Both the user and the satellite location are in the form of latitude, longitude and altitude.
These locations are converted to vectors in an XYZ coordinate system with the Earth's center as the zero vector `(0,0,0)`, the X axis aligned with the prime meridian and the Z axis going through the poles.
A simple vector subtraction gives the vector from the user to the satellite.
This vector gives the direction in which the arrow of the SatGazer should point.
This vector is now transformed to another coordinate system centered on the SatGazer device with the X axis pointing East, Y pointing North and Z pointing skywards.
Using this transformed vector, it's easy to compute the heading (aka. azimuth) and pitch (aka. altitude, elevation) of the satellite relative to the SatGazer's location.

### Moving Things (incomplete)

(Implemented in motor.py)

The two axes are each driven by a stepper motor.
To talk to these motors through the Raspberry Pi's GPIO pins, the `gpiozero` library is used.
For each step, the next motor pin in the sequence is activated (i.e. pulled high).

Because the mechanics for the azimuth have a 4:1 gear ratio, it takes four times as long to adjust the azimuth than it takes to adjust the elevation.
When the target is "behind" the SatGazer, it is therefore always quicker to point the arrow "backwards" than it is to rotate the top plate by more than 90 degrees.
Because of this, it is possible that the arrow may point North with the North indicator pointing South.

To conserve power, the stepper motors are turned off (coasting) when not moving.

### Web Server and API

The web server serves the GUI under the root URL `/`.
The GUI is really just a helper to send the proper HTTP requests to the rest of the server's API.

`GET /coast` turns off tracking and the stepper motors. The device stops moving.

`GET /calibrate` tells SatGazer that it is in the zero position. See the section about calibration.

`GET /track/<lat>/<long>/<sat_id>` starts tracking the satellite with the given ID. `<lat>` and `<long>` are the coordinates of the device.

`GET /driver/<azi>/<ele>` turns off tracking and aligns the arrow with to the given azimuth and elevation.

## Bill of Materials

The device consists of the following parts.

3D-printed parts:
- Base plate
- Top plate
- Heading gear
- Arrow

Electronics:
- Raspberry Pi Zero
- Transistor array board (2x)
- Stepper motor (unipolar) (2x)
- Battery module (optional)
- Various wires and cables

## Usage Instructions

### Getting an API key for N2YO.com

SatGazer uses n2yo.com's web API to obtain the positions of satellites.
This API requires an API key to be supplied along with the request.
You can obtain such a key for free by following the instructions [here](https://n2yo.com/api/).
Once you have your key, store it in a file `api.key` and place the file in the working directory from which you will launch the tracking script.

### Calibration

Before operation, SatGazer must be brought to a known orientation.
Calibration must be repeated after every start of the tracking script.

1. Orient the device such that the North indicator on the top plate is aligned to North.
2. Orient the arrow such that points straight up towards the sky. 
There is a small notch at the base of the "arrow tower" to check alignment.
Be careful and gentle!
Depending on the stepper motors, you may not be able to turn it by hand. 
In this case use the web GUI to move the arrow.
3. Once both axes are aligned, click the `calibrate` button in the web GUI.
The device is now in the `(0,0)` position.
4. Nice! The device is now calibrated.

When the tracking script starts, it assumes the device is in the `(0,0)` position.
This means that you can skip calibration if you start the script with the device already in the proper zero position.

### Checking Motors

To ensure that the stepper motors operate correctly, set both the heading and altitude to 90 using the web GUI.
Ensure that both axes move smoothly and that the arrow now indeed points East.

If the motors don't run smoothly or at all, check that the wiring corresponds to the pin assignments for the motors.
The order of the pins and wires matters! Also try a longer `STEP_TIME`.

If the arrow made a full rotation and now points up again, check that you haven't confused the two motors with each other.

If the arrow points West instead of East, check the North indicator of the top plate.
If the indicator points East, the altitude motor must be reversed.
If the indicator points West, the heading motor must be reversed.
To do that, add `reversed=True` when creating the motor, e.g.

```
# Note: Your pin assignments and step size may vary.
UnipolarMotor(22, 27, 17, 18, 5.625/32, reverse=True)
```

### Tracking a Satellite

To track a satellite, you need to know the coordinates of your own location and the NORAD ID of the satellite you want to track.
A good way to find this ID is [N2YO's search function](https://n2yo.com/database/).
Your own location can be found easily using Google Maps, for example.

Enter the information in the web GUI and hit submit.
The SatGazer device should not start tracking the satellite.

## Additional Notes

SatGazer was designed for tracking satellites but could in principle track any object with some code changes.

## Known Bugs and Feature Ideas

Ideas:
- Smooth tracking using variable stepping speed
- Automatically determine location using IP
- Show information in web GUI
- Don't immediately start tracking upon script start
- Autorun script at OS startup
- Improve parsing of coordinates
- Use azimuth and elevation instead of heading, pitch, altitude
- Make configuration easier (config file?)