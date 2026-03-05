#!/bin/bash
#PBS -N Gahenax_Mersenne
#PBS -o logs/mersenne_mpi.out
#PBS -e logs/mersenne_mpi.err
#PBS -l nodes=4:ppn=32
#PBS -l walltime=120:00:00
#PBS -q batch
#PBS -l pmem=2gb

cd $PBS_O_WORKDIR
module purge
module load python/3.10 openmpi/4.1.4
source venv/bin/activate
export PYTHONPATH=$(pwd)

echo "Starting Gahenax-Mersenne on PBS Cluster."
mpiexec python research/supercomputing/mpi_mersenne_sieve.py --p_start 80000000 --p_end 90000000
