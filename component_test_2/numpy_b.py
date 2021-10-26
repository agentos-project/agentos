import numpy as np


class NumpyTestB:
    def check_numpy_version(self):
        print()
        print(f"Checking if numpy version {np.__version__} is 1.20.0")
        assert np.__version__ == "1.20.0", "Check failed!"
        # min_digits kwarg added in numpy 1.21.0, raises TypeError in 1.20.0
        try:
            np.format_float_positional(1.0192, min_digits=4)
        except TypeError:
            print("\tCheck succeeded!")
        else:
            raise Exception("Check FAILED! Numpy import is broken")
