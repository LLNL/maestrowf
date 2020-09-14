#!/bin/bash
#SBATCH --partition=pbatch
#SBATCH --account=abank
#SBATCH --time=24:00:00
#SBATCH --job-name="scheduled-step"
#SBATCH --output="scheduled-step.out"
#SBATCH --error="scheduled-step.err"
#SBATCH --comment "scheduled"
#SBATCH --ntasks=4

echo "Do scheduled stuff"

