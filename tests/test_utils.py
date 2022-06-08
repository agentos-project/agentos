from pcs.utils import leaf_lists, transform_leaf


def test_transform_leaf():
    x = {1: [2, {3: [4, 5, 6]}]}  # Has four leaves: 2, 4, 5, 6.
    copy_of_x = {}
    for ll in leaf_lists(x):
        transform_leaf(x, copy_of_x, ll, lambda y: 2*y)
    assert copy_of_x == {1: [4, {3: [8, 10, 12]}]}
    assert x == {1: [2, {3: [4, 5, 6]}]}
