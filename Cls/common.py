#!/usr/bin/python
import numpy as np
import os

def get_tracer_name(ibin):
    if ibin in np.arange(5):
        name = 'DESgc{}'.format(ibin)
    elif ibin in np.arange(5, 9):
        name = 'DESwl{}'.format(ibin-5)
    elif ibin == 9:
        name = 'PLAcv'

    return name

def split_cls_all_array(cls_all, lbpw, bins, index_B, outdir):
    nmaps = cls_all.shape[0]

    for i in range(nmaps):
        if i in index_B:
            continue
        for j in range(i, nmaps):
            if j in index_B:
                continue
            cl_bins = [bins[i], bins[j]]
            tracer_names = [get_tracer_name(ibin) for ibin in cl_bins]
            fname = os.path.join(outdir, 'cls_{}_{}.npz'.format(*tracer_names))
            np.savez_compressed(fname, ells=lbpw, cls=cls_all[i, j])

def correct_minus_sign_sh(cls_all, index_sh):
    for i in range(cls_all.shape[0]):
        for j in range(cls_all.shape[1]):
            f = 1
            if i in index_sh:
                f *= -1
            if j in index_sh:
                f *= -1
            cls_all[i, j] *= f

    return cls_all

def load_cls_all_array_from_files(folder, bins, index_B):
    """ Load cls from DESxx_zbin arrays. """

    fname = os.path.join(folder, 'cls_{0}_{0}.npz'.format(get_tracer_name(0)))
    ells = np.load(fname)['ells']

    cls_all = np.zeros((len(bins), len(bins), ells.size))
    cls_Bx = np.zeros(ells.size)
    for i, ibin in enumerate(bins):
        tr1 = get_tracer_name(ibin)
        if i in index_B:
            continue
        for j, jbin in enumerate(bins[i:], i):
            tr2 = get_tracer_name(jbin)
            if j in index_B:
                continue
            fname = os.path.join(folder, 'cls_{}_{}.npz'.format(tr1, tr2))
            print(fname)
            cls_all[i, j] = np.load(fname)['cls']
            cls_all[j, i] = cls_all[i, j]

    return ells, cls_all

###########
# Functions to read Cls in /mnt/extraspace/evam/S8z/
###########

def load_thcls_Eva(th_outdir, file_prefix, nmaps):
    cls_arr = []
    for i in range(nmaps):
        for j in range(i, nmaps):
            fname = os.path.join(th_outdir, file_prefix + '_{}_{}.txt'.format(i, j))
            if not os.path.isfile(fname): #spin0-spin0
                raise ValueError('Missing workspace: ', fname)

            cls_arr.append(np.loadtxt(fname, usecols=1))

    ell = np.loadtxt(fname, usecols=0)

    return ell, np.array(cls_arr)

def load_thcls_gk_Eva(nmaps_g, nmaps_k):
    th_outdir = '/mnt/extraspace/evam/S8z/Clsgk/'
    file_prefix = 'DES_Cls_gk_lmax3xNside'
    cls_arr = []
    for i in range(nmaps_g):
        for j in range(nmaps_k):
            fname = os.path.join(th_outdir, file_prefix + '_{}_{}.txt'.format(i, j))
            if not os.path.isfile(fname): #spin0-spin0
                raise ValueError('Missing workspace: ', fname)

            cls_arr.append(np.loadtxt(fname, usecols=1))

    ell = np.loadtxt(fname, usecols=0)

    return ell, np.array(cls_arr)

def load_thcls_Planck_Eva():
    fdir = '/mnt/extraspace/evam/S8z/ClsPlanck/'
    cls_arr = []
    for i in range(5):
        fname = os.path.join(fdir, 'DESPlanck_Cls_gk_lmax3xNside_{}.txt'.format(i))
        cls_arr.append(np.loadtxt(fname, usecols=1))
    for i in range(4):
        fname = os.path.join(fdir, 'DESPlanck_Cls_kk_lmax3xNside_{}.txt'.format(i))
        cls_arr.append(np.loadtxt(fname, usecols=1))
        cls_arr.append(cls_arr[-1] * 0)

    fname = os.path.join(fdir, 'Planck_Cls_kk_lmax3xNside.txt')
    cls_arr.append(np.loadtxt(fname, usecols=1))
    ell = np.loadtxt(fname, usecols=0)

    return ell, np.array(cls_arr)

def load_cls_all_matrix_th_Eva():
    # All th_ell are the same
    th_outdir = '/mnt/extraspace/evam/S8z/Clsgg/'
    th_ell, Clsgg_ar = load_thcls(th_outdir, 'DES_Cls_lmax3xNside', 5)

    th_outdir = '/mnt/extraspace/evam/S8z/Clskk/'
    th_ell, Clskk_ar = load_thcls(th_outdir, 'DES_Cls_kk_lmax3xNside', 4)

    th_outdir = '/mnt/extraspace/evam/S8z/Clsgk/'
    th_ell, Clsgk_ar = load_thcls_gk(5, 4)

    th_outdir = '/mnt/extraspace/evam/S8z/ClsPlanck/'
    th_ell, ClsPlanck_ar = load_thcls_Planck()

    # Checked that all EE's are the same as in the array.
    Clskk_full_mat = np.zeros((8, 8, th_ell.shape[0]))
    i, j = np.triu_indices(4)
    Clskk_full_mat[::2, ::2][i, j] = Clskk_ar
    Clskk_full_mat[::2, ::2][j, i] = Clskk_ar
    i, j = np.triu_indices(8)
    Clskk_ar_full = Clskk_full_mat[i, j]

    th_cls_all = np.zeros((14, 14, th_ell.shape[0]))

    i, j = np.triu_indices(5)
    th_cls_all[:5, :5][i, j] = Clsgg_ar

    i, j = np.triu_indices(8)
    th_cls_all[5:-1, 5:-1][i, j] = Clskk_ar_full

    th_cls_all[:, -1] = ClsPlanck_ar

    for i in range(5):
        th_cls_all[i, 5:-1:2] = Clsgk_ar[i * 4 : (i + 1) * 4]

    i, j = np.triu_indices(14)
    th_cls_all_ar = th_cls_all[i, j]
    th_cls_all[j, i] = th_cls_all_ar

    return th_ell, th_cls_all

###########
# END functions to read Cls in /mnt/extraspace/evam/S8z/
###########

if __name__ == '__main__':
    output_folder = '/mnt/extraspace/gravityls_3/S8z/Cls/all_together'

    # ####
    # #### Unnecessary anymore. It is done in the main script.
    # ####
    # index_sh = [5, 6, 7, 8, 9, 10, 11, 12]
    # fname = os.path.join(output_folder,  "cl_all_with_noise.npz")
    # cls_all_file = np.load(fname)
    # lbpw, cls_all = cls_all_file['l'], cls_all_file['cls']
    # cls_all = correct_minus_sign_sh(cls_all, index_sh)
    # np.savez_compressed(fname, l=lbpw, cls=cls_all)

    # fname = os.path.join(output_folder,  "cl_all_no_noise.npz")
    # cls_all_file = np.load(fname)
    # lbpw, cls_all = cls_all_file['l'], cls_all_file['cls']
    # cls_all = correct_minus_sign_sh(cls_all, index_sh)
    # np.savez_compressed(fname, l=lbpw, cls=cls_all)

    bins = [0, 1, 2, 3, 4] + [5, 5] + [6, 6] + [7, 7] + [8, 8] + [9]
    index_B = [6, 8, 10, 12]
    split_cls_all_array(cls_all, lbpw, bins, index_B, output_folder)
