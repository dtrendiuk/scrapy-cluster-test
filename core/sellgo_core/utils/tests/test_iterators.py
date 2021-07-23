from sellgo_core.utils.iterators import list_split


def test_list_split():
    lst = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    n = 2

    for chunk in list_split(lst, n):
        assert len(chunk) == 2
