#!/bin/bash
#SBATCH --job-name=Gahenax_Mersenne
#SBATCH --output=logs/mersenne_mpi_%j.out
#SBATCH --nodes=4                   
#SBATCH --ntasks-per-node=32        
#SBATCH --time=120:00:00             
#SBATCH --partition=compute         

module purge
module load python/3.10 openmpi/4.1.4
source venv/bin/activate
export PYTHONPATH=$(pwd)

echo "Starting Gahenax-Mersenne on $SLURM_JOB_NUM_NODES nodes."
mpirun python research/supercomputing/mpi_mersenne_sieve.py --p_start 80000000 --p_end 90000000
