#!/usr/bin/python

from __future__ import print_function
from scipy.interpolate import interp1d
import os
import sys
import pymaster as nmt
import numpy as np
import healpy as hp

# pylint: disable=C0103,C0111

##############################################################################
##############################################################################
output_folder = '/mnt/extraspace/gravityls_3/S8z/Cls'

data_folder = '/mnt/extraspace/damonge/S8z_data/derived_products'
des_folder_gcl = 'des_clustering'
des_nside = 4096
if des_nside != 4096:
    des_folder_gcl += '_{}'.format(des_nside)

des_mask = 'mask_ns{}.fits'.format(des_nside)
des_bins = 5

des_data_folder = os.path.join(data_folder, des_folder_gcl)

des_mask_path = os.path.join(des_data_folder, des_mask)
des_th_cls_path = '/mnt/extraspace/evam/S8z/'

##############################################################################
########### Read mask ###########
##############################################################################
des_mask = hp.read_map(des_mask_path, verbose=False)

##############################################################################
########### Read map ###########
##############################################################################
# Read one map (gg) (as they all share the same mask)
map_file = os.path.join(des_data_folder, 'map_counts_w_bin0_ns{}.fits'.format(des_nside))  # Same mask, just one field needed
des_mapi = hp.read_map(map_file)

des_N_mean = des_mapi.sum() / des_mask.sum()
des_mapi_dg = des_mapi / (des_N_mean * des_mask) - 1
des_mapi_dg[np.isnan(des_mapi_dg)] = 0.  # This is the map for Cl's

##############################################################################
############## Set up binning scheme ##############
##########################################nvim####################################
fsky = np.mean(des_mask)
d_ell = int(1./fsky)
b = nmt.NmtBin(des_nside, nlb=d_ell)

##############################################################################
################ Read Th. cls ###############
##############################################################################

##############################################################################
def load_thcls(th_outdir):
    cls_arr = []
    for i in range(des_bins):
        for j in range(i, des_bins):
            fname = os.path.join(th_outdir, 'DES_Cls_lmax3xNside_{}_{}.txt'.format(i, j))
            if not os.path.isfile(fname): #spin0-spin0
                raise ValueError('Missing workspace: ', fname)

            cls_arr.append(np.loadtxt(fname, usecols=1))

    ell = np.loadtxt(fname, usecols=0)

    return ell, np.array(cls_arr)
##############################################################################

th_ell, des_th_cls_arr = load_thcls(des_th_cls_path)

des_th_cl00_matrix = np.empty((des_bins, des_bins, len(th_ell)),
                              dtype=des_th_cls_arr[0].dtype)
i, j = np.triu_indices(des_bins)
des_th_cl00_matrix[i, j] = des_th_cls_arr
des_th_cl00_matrix[j, i] = des_th_cls_arr

##############################################################################
################# Add shot noise Cls to th's ones  #################
##############################################################################
fname = os.path.join(output_folder, "des_w_cl_shot_noise_ns{}.npz".format(des_nside))
if not os.path.isfile(fname):
    raise ValueError('Missing shot noise: ', fname)

des_Nls_file = np.load(fname)
des_Nls_ell = des_Nls_file['l']
des_Nls_arr = des_Nls_file['cls']

for i, nls in enumerate(des_Nls_arr):
    des_th_cl00_matrix[i, i] += interp1d(des_Nls_ell, nls, bounds_error=False,
                                         fill_value=(nls[0], nls[-1]))(th_ell)


##############################################################################
##############################################################################
####################### NaMaster-thing part ##################################
##############################################################################
##############################################################################

des_f0 = nmt.NmtField(des_mask, [des_mapi_dg])
f0 = des_f0

##############################################################################
###############  Load already computed workspace   ###############
##############################################################################
fname = os.path.join(output_folder, 'des_w00_ns{}.dat'.format(des_nside))
w00 = nmt.NmtWorkspace()
if not os.path.isfile(fname): #spin0-spin0
    w00.compute_coupling_matrix(f0, f0, b)  # raise ValueError('Missing workspace: ', fname)
    w00.write_to(fname)
else:
    w00.read_from(fname)

##############################################################################
################### Compute covariance coupling coefficients #################
##############################################################################
fname = os.path.join(output_folder, 'des_cw_ns{}.npz'.format(des_nside))
cw = nmt.NmtCovarianceWorkspace()
if not os.path.isfile(fname):
    cw.compute_coupling_coefficients(f0, f0)
    cw.write_to(fname)
else:
    cw.read_from(fname)

##############################################################################
#################  Compute coupling cov matrix for bins i, j #################
##############################################################################

# nmt.gaussian_covariance(cw, spin_a1, spin_a2, spin_b1, spin_b2,
#                         cla1b1, cla1b2, cla2b1, cla2b2,
#                         wa, wb=None)

list_bins = [str(i) for i in range(des_bins)]

cls_bins = []
for i in list_bins:
    tmp = []
    for j in list_bins:
        tmp.append(i+j)
    cls_bins.append(tmp)

cls_bins = np.array(cls_bins)

cov_bins = []
i, j = np.triu_indices(des_bins)
for clij in cls_bins[i, j]:
    tmp = []
    for clkl in cls_bins[i, j]:
        tmp.append(clij+ clkl)
    cov_bins.append(tmp)

cov_bins = np.array(cov_bins)
i, j = np.triu_indices(cov_bins.shape[0])

cov_to_compute = cov_bins[i, j]

for step, fields in enumerate(cov_to_compute):
    bin_a1 = int(fields[0])
    bin_a2 = int(fields[1])
    bin_b1 = int(fields[2])
    bin_b2 = int(fields[3])

    cla1b1 = des_th_cl00_matrix[bin_a1, bin_b1]
    cla1b2 = des_th_cl00_matrix[bin_a1, bin_b2]
    cla2b1 = des_th_cl00_matrix[bin_a2, bin_b1]
    cla2b2 = des_th_cl00_matrix[bin_a2, bin_b2]

    fname = os.path.join(output_folder, 'des_c0000_{}.npz'.format(fields))
    if os.path.isfile(fname):
        continue

    sys.stdout.write("Computing:{}\n".format(fname))
    sys.stdout.write("Computation {} out of {}\n".format(step, cov_to_compute.shape[0]))
    c0000 = nmt.gaussian_covariance(cw, 0, 0, 0, 0,
                                    [cla1b1], [cla1b2], [cla2b1], [cla2b2], w00)
    np.savez_compressed(fname, c0000)
