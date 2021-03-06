#!/bin/bash

nside=4096
nrot=100
irot0=90

#addqueue -q cmb -m 20 -n 1 /usr/bin/python3 des_shear_tests.py --nside 4096 --bin-number 3
#exit

# Clustering
echo addqueue -q cmb -m 12 -n 1 /usr/bin/python3 des_clustering.py ${nside}

# Shear
#  - Loop over shape catalogs
for cat_name in metacal im3shape
do
    #  - Loop over redshift bins
    for bin in 0 1 2 3
    do
	echo ${cat_name} ${nside} ${bin}
	echo addqueue -q cmb -m 12 -n 1 /usr/bin/python3 des_shear.py --catalog ${cat_name} --nside ${nside} --bin-number ${bin} --recompute
	#  - Loop over random rotations (needed for noise bias estimation)
	addqueue -q cmb -m 12 -n 1 ./run_des_rotations.sh ${nside} ${nrot} ${irot0} ${cat_name} ${bin}
    done
done
