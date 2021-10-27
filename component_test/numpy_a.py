import numpy as np


class NumpyTestA:
    def check_numpy_version(self):
        print()
        print(f"Checking if numpy version {np.__version__} is 1.21.3")
        assert np.__version__ == "1.21.3", "Check failed!"
        # min_digits kwarg added in numpy 1.21.0, should be ok
        np.format_float_positional(1.0192, min_digits=4)
        print("\tCheck succeeded!")
