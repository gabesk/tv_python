from math import sin, pi

class FirFilterLowPassRect:
    """A low-pass FIR filter created using the window method."""

    def __init__(self, num_taps, fc):
        self.fc = fc
        self.num_taps = num_taps

        # Create the impluse response of the filter, which is just the infinite
        # response of the normalized scaled sinc function, truncated by however
        # many taps specified.
        self.responses = []
        # So, for example, for 8 taps, this would be -4,-3,-2,-1,0,1,2,3
        for x in range(num_taps):
            n = x - num_taps//2
            self.responses.append(self.__sinc(n))

        # Create space to hold the previous samples, up to the number of taps
        # so that they can be applied against the sinc response each time a new
        # filter value is desired.
        self.memory = [0] * num_taps

    def __sinc(self, x):
        """Returns the normalized sinc function of x scaled by the cutoff
        frequency desired for the low pass filter.
        (With a maximum cutoff of the Nyquist frequency of 0.5).
        See http://www.labbookpages.co.uk/audio/firWindowing.html
        for more details.
        """
        if x == 0:
            y = 2 * self.fc
        else:
            y = sin(2 * pi * self.fc * x)/(pi * x)

        return y

    def filter(self, sample):
        '''Accepts a new sample and returns the response of the filter to that
        sample.'''
        # Yes, this could be a ring buffer for greater efficiency, but this is
        # more intuitive as to what's going on.
        self.memory.append(sample)
        self.memory.pop(0)

        responses_summation = 0
        for x in range(self.num_taps):
            responses_summation += self.memory[x] * self.responses[x]

        return responses_summation