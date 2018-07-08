from __future__ import absolute_import, division, print_function

import pickle

import numpy as np
import pytest

import xarray as xr
import xarray.ufuncs as xu

from . import (
    assert_array_equal, assert_identical as assert_identical_, mock,
    raises_regex, requires_np113)


def assert_identical(a, b):
    assert type(a) is type(b) or (float(a) == float(b))  # noqa
    if isinstance(a, (xr.DataArray, xr.Dataset, xr.Variable)):
        assert_identical_(a, b)
    else:
        assert_array_equal(a, b)


@requires_np113
def test_unary():
    args = [0,
            np.zeros(2),
            xr.Variable(['x'], [0, 0]),
            xr.DataArray([0, 0], dims='x'),
            xr.Dataset({'y': ('x', [0, 0])})]
    for a in args:
        assert_identical(a + 1, np.cos(a))


@requires_np113
def test_binary():
    args = [0,
            np.zeros(2),
            xr.Variable(['x'], [0, 0]),
            xr.DataArray([0, 0], dims='x'),
            xr.Dataset({'y': ('x', [0, 0])})]
    for n, t1 in enumerate(args):
        for t2 in args[n:]:
            assert_identical(t2 + 1, np.maximum(t1, t2 + 1))
            assert_identical(t2 + 1, np.maximum(t2, t1 + 1))
            assert_identical(t2 + 1, np.maximum(t1 + 1, t2))
            assert_identical(t2 + 1, np.maximum(t2 + 1, t1))


@requires_np113
def test_binary_out():
    args = [1,
            np.ones(2),
            xr.Variable(['x'], [1, 1]),
            xr.DataArray([1, 1], dims='x'),
            xr.Dataset({'y': ('x', [1, 1])})]
    for arg in args:
        actual_mantissa, actual_exponent = np.frexp(arg)
        assert_identical(actual_mantissa, 0.5 * arg)
        assert_identical(actual_exponent, arg)


@requires_np113
def test_groupby():
    ds = xr.Dataset({'a': ('x', [0, 0, 0])}, {'c': ('x', [0, 0, 1])})
    ds_grouped = ds.groupby('c')
    group_mean = ds_grouped.mean('x')
    arr_grouped = ds['a'].groupby('c')

    assert_identical(ds, np.maximum(ds_grouped, group_mean))
    assert_identical(ds, np.maximum(group_mean, ds_grouped))

    assert_identical(ds, np.maximum(arr_grouped, group_mean))
    assert_identical(ds, np.maximum(group_mean, arr_grouped))

    assert_identical(ds, np.maximum(ds_grouped, group_mean['a']))
    assert_identical(ds, np.maximum(group_mean['a'], ds_grouped))

    assert_identical(ds.a, np.maximum(arr_grouped, group_mean.a))
    assert_identical(ds.a, np.maximum(group_mean.a, arr_grouped))

    with raises_regex(ValueError, 'mismatched lengths for dimension'):
        np.maximum(ds.a.variable, ds_grouped)


@requires_np113
def test_alignment():
    ds1 = xr.Dataset({'a': ('x', [1, 2])}, {'x': [0, 1]})
    ds2 = xr.Dataset({'a': ('x', [2, 3]), 'b': 4}, {'x': [1, 2]})

    actual = np.add(ds1, ds2)
    expected = xr.Dataset({'a': ('x', [4])}, {'x': [1]})
    assert_identical_(actual, expected)

    with xr.set_options(arithmetic_join='outer'):
        actual = np.add(ds1, ds2)
        expected = xr.Dataset({'a': ('x', [np.nan, 4, np.nan]), 'b': np.nan},
                              coords={'x': [0, 1, 2]})
        assert_identical_(actual, expected)


@requires_np113
def test_kwargs():
    x = xr.DataArray(0)
    result = np.add(x, 1, dtype=np.float64)
    assert result.dtype == np.float64


@requires_np113
def test_xarray_defers_to_unrecognized_type():

    class Other(object):
        def __array_ufunc__(self, *args, **kwargs):
            return 'other'

    xarray_obj = xr.DataArray([1, 2, 3])
    other = Other()
    assert np.maximum(xarray_obj, other) == 'other'
    assert np.sin(xarray_obj, out=other) == 'other'


@requires_np113
def test_xarray_handles_dask():
    da = pytest.importorskip('dask.array')
    x = xr.DataArray(np.ones((2, 2)), dims=['x', 'y'])
    y = da.ones((2, 2), chunks=(2, 2))
    result = np.add(x, y)
    assert result.chunks == ((2,), (2,))
    assert isinstance(result, xr.DataArray)


@requires_np113
def test_dask_defers_to_xarray():
    da = pytest.importorskip('dask.array')
    x = xr.DataArray(np.ones((2, 2)), dims=['x', 'y'])
    y = da.ones((2, 2), chunks=(2, 2))
    result = np.add(y, x)
    assert result.chunks == ((2,), (2,))
    assert isinstance(result, xr.DataArray)


@requires_np113
def test_gufunc_methods():
    xarray_obj = xr.DataArray([1, 2, 3])
    with raises_regex(NotImplementedError, 'reduce method'):
        np.add.reduce(xarray_obj, 1)


@requires_np113
def test_out():
    xarray_obj = xr.DataArray([1, 2, 3])

    # xarray out arguments should raise
    with raises_regex(NotImplementedError, '`out` argument'):
        np.add(xarray_obj, 1, out=xarray_obj)

    # but non-xarray should be OK
    other = np.zeros((3,))
    np.add(other, xarray_obj, out=other)
    assert_identical(other, np.array([1, 2, 3]))


@requires_np113
def test_gufuncs():
    xarray_obj = xr.DataArray([1, 2, 3])
    fake_gufunc = mock.Mock(signature='(n)->()', autospec=np.sin)
    with raises_regex(NotImplementedError, 'generalized ufuncs'):
        xarray_obj.__array_ufunc__(fake_gufunc, '__call__', xarray_obj)


def test_xarray_ufuncs_deprecation():
    with pytest.warns(PendingDeprecationWarning, match='xarray.ufuncs'):
        xu.cos(xr.DataArray([0, 1]))


def test_xarray_ufuncs_pickle():
    a = 1.0
    cos_pickled = pickle.loads(pickle.dumps(xu.cos))
    assert_identical(cos_pickled(a), xu.cos(a))
