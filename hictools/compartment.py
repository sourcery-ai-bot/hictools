"""
Tools for compartment analysis.
"""
# TODO(zhongquan789@126.com): handling intra and inter interaction

from typing import Callable

import numpy as np
import scipy.linalg as nl
from scipy import sparse

from .utils import is_symmetric


def linear_bins(lo, hi):
    return np.r_[0, np.arange(lo, hi)]


def get_decay(mat: np.ndarray,
              span_fn: Callable[[int, int], np.ndarray] = linear_bins,
              ndiags: int = None,
              ignore_nan: bool = True,
              ignore_zero: bool = True,
              record: bool = False) -> np.ndarray:
    """Calculate mean contact across each diagonal.

    :param mat: np.ndarray. The matrix to compute.
    :param span_fn: callable. The callable object to seapate the linear space in to larger part.
    :param ndiags: int.
    :param ignore_nan: bool. If ignore counts of nan values in each diagonal.
    :param ignore_zero: bool. If ignore counts of zero values in each diagonal.
    :param record: bool. if record the number of valid caontacts in the result.
    :return: np.ndarray.
    """
    length = mat.shape[0]
    ndiags = ndiags if ndiags is not None else length
    bins_span = span_fn(0, length)
    decay = np.zeros(length, dtype=mat.dtype)

    if record:
        nums_array = np.zeros(length, dtype=np.int)

    for start, end in zip(bins_span[:-1], bins_span[1:]):
        if start >= ndiags:
            continue
        sum_counts = 0
        num_pixels = 0
        for offset in range(start, end):
            diag = mat.diagonal(offset)
            if ignore_nan and ignore_zero:
                sub_data = diag[(diag != 0) & (~np.isnan(diag))]
                sum_counts += np.sum(sub_data)
            elif ignore_nan:
                sub_data = diag[~np.isnan(diag)]
                sum_counts += np.sum(sub_data)
            elif ignore_zero:
                sub_data = diag[diag != 0]
                sum_counts += np.nansum(sub_data)
            else:
                sub_data = diag
                sum_counts += np.sum(sub_data)
            num_pixels += sub_data.size

        average = (sum_counts / num_pixels) if num_pixels else 0
        decay[start: end] = average
        if record:
            nums_array[start: end] = num_pixels

    if record:
        results = np.zeros(
            shape=length,
            dtype=[('average', mat.dtype), ('number', np.int)]
        )
        results['average'] = decay
        results['number'] = nums_array
        return results

    else:
        return decay


def eig(mat, vecnum=3):
    """

    :param mat:
    :param vecnum:
    :return:
    """
    if is_symmetric(mat):
        eigvals, eigvecs = sparse.linalg.eigsh(mat, vecnum)
    else:
        eigvals, eigvecs = sparse.linalg.eigs(mat, vecnum)

    order = np.argsort(-np.abs(eigvals))
    eigvals = eigvals[order]
    eigvecs = eigvecs.T[order]

    return eigvals, eigvecs


def pca(mat, vecnum=3):
    """

    :param mat:
    :param vecnum:
    :return:
    """
    center = mat - np.mean(mat, axis=0)
    cov = np.dot(center.T, center)
    eigvals, eigvecs = sparse.linalg.eigsh(cov, vecnum)
    eigvals /= (mat.shape[0] - 1)

    return eigvals[::-1], eigvecs[:, ::-1].T


def get_pca_compartment(mat, vecnum: int = 3):
    """Fetch A/B compartmentation through principle component analysis(use svd).

    :return type: np.ndarray. positive values represent A compartment and negative
    values represent B compartment.
    """
    _, components = pca(mat, vecnum=vecnum)

    return components


def get_eigen_compartment(mat, vecnum: int = 3, subtract_mean=False, divide_by_mean=False):
    """Fetch A/B compartmentation through eigen value decompositon.

    :return type: np.ndarray. Positive values represent A compartment and negative values represent B compartment.
    """
    if subtract_mean or divide_by_mean:
        mat = mat.copy()
        mean = np.mean(mat)
        if subtract_mean:
            mat -= mean
        else:
            mat /= mean

    _, eigvecs = eig(mat, vecnum=vecnum)

    return eigvecs


def corr_sorter(chrom_matrix, eigvecs: np.ndarray, corr=None, **kwargs):
    """Choose the most possible vector which may infer the compartment A/B seperation based on pearson correlation matrix.
        1. Choose vector:
            In general, the sums of pearson correlation value within A and B is larger than the sums of pearson
            correlation value across A-B.
        2. Choose AB:
            In general, the interactions within A are stronger than the interactions within B.

    :param chrom_matrix:
    :param eigvecs:
    :param corr:
    :param kwargs:
    :return:
    """

    def mean_corr(mat, compartment):

        com_mask1 = compartment > 0
        com_mask2 = compartment < 0
        return (
            np.mean(mat[np.ix_(com_mask1, com_mask1)]),
            np.mean(mat[np.ix_(com_mask2, com_mask2)]),
            np.mean(mat[np.ix_(com_mask1, com_mask2)])
        )

    coms = []
    for i, component in enumerate(eigvecs):
        # In some cases the divergence between max-value in A/B is too large.
        diverse = np.abs(np.min(component)) / np.max(component)
        coma = component > 0
        ratio = len(np.where(coma)[0]) / len(np.where(~coma)[0])
        if ((diverse > 10)
                or (diverse < 0.1)
                or (ratio > 15)
                or (ratio < 1 / 15)):
            possible = False
        else:
            possible = True

        if corr is None:
            chrom_matrix.corr(**kwargs)
        mean_aa, mean_bb, mean_ab = mean_corr(mat=corr, compartment=component)

        coms.append(
            (
                component * np.sign(mean_aa - mean_bb),
                mean_aa + mean_bb - 2 * mean_ab,
                possible
            )
        )

    sorted_coms = sorted(coms, key=lambda x: (x[2], x[1]), reverse=True)

    return np.array([com[0] for com in sorted_coms])


def plain_sorter(chrom_matrix, eigvecs: list, *kwargs):
    return np.array(eigvecs)


class Pca(object):
    """Implementation of principal component analysis. Reference: sklearn
    """

    def __init__(self, mat):
        """
        :param mat: numpy.ndarray

        Marks:
            mat : original matrix
            mean : means of columns of mat
            X(center) : centered original matrix. X = mat - center
            A : matrix generatd by casting X to components
            U : X = U*S*Vh
            S : X = U*S*Vh
            Vh : X = U*S*Vh

        Attention:
            Uses scipy.linalg.svd(full_matrices=True)
        """
        if isinstance(mat, np.matrix):
            mat = np.array(mat)
        self._center = None
        self._mean = None
        self.nrow, self.ncol = mat.shape
        self.U, self.S, self.Vh = self._pca(mat)
        self.n_components = self.S.shape[0]
        self._variance = None
        self._variance_ratio = None

    @property
    def mat(self):
        """Return the original matrix.
        :return type: np.ndarray.
        """
        return self._center + self._mean

    @property
    def components(self):
        """Return components matrix. This matrix is Vh.
        :return type: np.ndarray.
        """
        return self.Vh

    @property
    def singular_values(self):
        """Return rank(mat) singular values.
        :return type: np.ndarray.
        """
        return self.S

    @property
    def variance(self):
        """Return S**2 / (nrow - 1).
        :return type: np.ndarray.
        """
        if self._variance is None:
            self._variance = self.S ** 2 / (self.nrow - 1)
        return self._variance

    @property
    def variance_ratio(self):
        """Return S**2 / sum(S**2).
        :return type: np.ndarray.
        """
        if self._variance_ratio is None:
            self._variance_ratio = self._variance / self.variance.sum()
        return self._variance_ratio

    def transform(self):
        """Cast X to the space of V.
        formula:
            A = XV
        """
        return self.shrink_c(n=self.n_components)

    def inverse_transform(self, A):
        """Restore the original matrix from transformed matrix
        :return type: np.ndarray.
        formula:
            X = AVh = XVVh
            mat = X + mean
        """
        return np.dot(A, self.Vh[:self.n_components, :]) + self._mean

    def shrink_c(self, n=None):
        """Dimension reduction from X(m, n) to X(m, r) r <= n
        :return type: np.ndarray.
        formula:
            new_X = X(m,n) * V(n,r)
        or: new_X = U(m,r) * S(r,r)
        """
        if n is None:
            n = self.ncol
        if not (1 <= n <= self.ncol):
            raise ValueError("Wrong n. n must within [1, ncol]")

        return np.dot(self._center, self.Vh.T[:, :n])

    def shrink_r(self, n=None):
        """Dimension reduction from X(m, n) to X(r, n) r <= m
        :return type: np.ndarray.
        formula:
            new_X = Uh(r,m) * X(m,n)
        or: new_X = S(r,r) * Vh(r,n)
        """
        if n is None:
            n = self.nrow
        if not (1 <= n <= self.nrow):
            raise ValueError("Wrong n. n must within [1, nrow]")

        return np.dot(self.U.T[:n, :], self._center)

    def reconstruct(self, start, end=None):
        """Reconstruct the matrix from certain portions of U and Vh.
        :return type: np.ndarray.
        formula:
            new_X = X(m,n) * V(n,i:j) * Vh(i:j,n)
        or: new_X = U(m,i:j) * S(i:j, i:j) * Vh(i:j,n)
            new_mat = new_X + mean
        """
        if end is None:
            end = start
            start = 0
        if not (0 <= start < end) or end > self.ncol:
            raise IndexError("Wrong start and end.")
        # X*(V1)*(V1t) + X*(V2)*(V2t) + ...
        return np.dot(np.dot(self._center, self.Vh[start:end, :].T),
                      self.Vh[start:end, :]) + self._mean

    def _pca(self, mat):
        """Center the matrix and caluculate the centered matrix's SVD decomposion U*S*Vh.
        Uses scipy.linaly.svd(full_matrices=True).
        :return U: np.ndarray.
        :return S: np.ndarray.
        :return Vh: np.ndarray.
        """
        self._mean = np.mean(mat, axis=0)
        self._center = mat - self._mean
        U, S, Vh = nl.svd(self._center, full_matrices=True, compute_uv=True)
        U, Vh = self._flip_svd(U, Vh)

        return U, S, Vh

    @staticmethod
    def _flip_svd(U, Vh, u_based_decision=True):
        """Ensure the same output_data (U/Vh) of the same matrix X.
        Eusure the largest(absolute value) values in cols of U(or rows of Vh) are always positive.
        This method is borrowed from _flip_svd method in sklearn.
        """
        if u_based_decision:
            max_abs_cols = np.argmax(np.abs(U), axis=0)
            signs = np.sign(U[max_abs_cols, range(U.shape[1])])
        else:
            max_abs_rows = np.argmax(np.abs(Vh), axis=1)
            signs = np.sign(Vh[range(Vh.shape[0]), max_abs_rows])

        len_signs = signs.shape[0]
        len_u = U.shape[0]
        len_vh = Vh.shape[0]
        if len_signs > len_u:
            U *= signs[:len_u]  # * row vector
        else:
            U[:, :len_signs] *= signs

        if len_signs > len_vh:
            Vh *= signs[:len_vh, np.newaxis]  # * col vector
        else:
            Vh[:len_signs, :] *= signs[:, np.newaxis]

        return U, Vh


class SliceMixin(object):

    @staticmethod
    def _fill_slice(slice_, length):
        if isinstance(slice_, int):
            slice_ = slice(slice_, slice_ + 1, 1)
        else:
            start, stop, step = slice_.start, slice_.stop, slice_.step
            if start is None:
                start = 0
            if stop is None:
                stop = length
            if step is None:
                step = 1
            slice_ = slice(start, stop, step)

        return slice_

    @staticmethod
    def _is_slices(slices):
        try:
            for slice_ in slices:
                if not isinstance(slice_, slice):
                    return False
            return True
        except TypeError as e:
            return isinstance(slices, slice)

    def _check_slices(self, slices, lengths, check_forward=False):
        if not self._is_slices(slices):
            raise TypeError('Not slices')

        if isinstance(slices, slice):
            slices = (slices,) * len(lengths)

        for slice_, length in zip(slices, lengths):
            filled_slice = self._fill_slice(slice_, length)
            if (check_forward
                    and (filled_slice.stop < filled_slice.start)):
                raise ValueError("Slice's stop is smaller than start")

            yield filled_slice


class Toeplitz(SliceMixin):
    __slots__ = ('_col', '_row')

    def __init__(self, col, row=None):
        self._col = col
        self._row = col if row is None else row

    def __getitem__(self, items):
        row_slice, col_slice = tuple(self._check_slices(
            items,
            (self._col.size, self._row.size),
            check_forward=True)
        )
        n_diags = col_slice.start - row_slice.start
        height = row_slice.stop - row_slice.start
        width = col_slice.stop - col_slice.start

        if height == 1 and width == 1:
            array = self._row if n_diags >= 0 else self._col
            return array[n_diags]

        else:
            if n_diags >= 0:
                harray = self._row[n_diags: n_diags + width]
                varray = self._row[:n_diags + 1][::-1][:-1]
                if n_diags < height:
                    varray = np.r_[varray, self._row[:height - n_diags]]
                else:
                    varray = varray[:height]
            else:
                n_diags *= -1
                varray = self._col[n_diags: n_diags + height]
                harray = self._col[:n_diags + 1][::-1][:-1]
                if n_diags < width:
                    harray = np.r_[harray, self._col[:width - n_diags]]
                else:
                    harray = harray[:width]

            ma = nl.toeplitz(varray[::row_slice.step], harray[::col_slice.step])

            return ma.ravel() if ma.size == 1 else ma


class Expected(Toeplitz):
    __slots__ = ('_col', '_row')

    def __init__(self, decay):
        super().__init__(decay)


if __name__ == '__main__':
    pass
