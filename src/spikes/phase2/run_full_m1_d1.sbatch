#!/bin/bash
#SBATCH --job-name=m1-d1-full
#SBATCH --partition=singhlab-gpu
#SBATCH --gres=gpu:a6000:1
#SBATCH --cpus-per-task=6
#SBATCH --mem=32G
#SBATCH --time=1:00:00
#SBATCH --output=/hpc/group/singhlab/user/emt70/rp1_project/dax-gen_project/runs/phase2_m1_d1/full/slurm-%j.out

set -euo pipefail

REPO=/hpc/group/singhlab/user/emt70/rp1_project/dax-gen_project
OUT_DIR="$REPO/runs/phase2_m1_d1/full"
mkdir -p "$OUT_DIR"

echo "=== Provenance ==="
echo "Start: $(date -Iseconds)"
echo "Node: $(hostname)"
nvidia-smi -L
echo "Repo SHA: $(git -C "$REPO" rev-parse HEAD)"
echo "Repo dirty check:"
DIRTY=$(git -C "$REPO" status --porcelain)
if [ -n "$DIRTY" ]; then
    echo "ERROR: repo is dirty, aborting for reproducibility:"
    echo "$DIRTY"
    exit 1
fi
echo "(clean)"
echo "Input file hashes:"
sha256sum "$REPO/data/curated/d1_ppi/train.csv" "$REPO/data/curated/d1_ppi/test.csv"
cp "$0" "$OUT_DIR/submitted_script.sbatch"

echo "=== Training ==="
cd "$REPO/src/spikes/phase2"
/hpc/home/emt70/micromamba/envs/esmc/bin/python -u train_m1.py \
    --data-dir "$REPO/data/curated/d1_ppi" \
    --out-dir "$OUT_DIR" \
    --epochs 15 \
    --lr 1e-3 \
    --batch-size 256 \
    --embed-batch-size 32 \
    --device cuda

echo "=== Evaluation ==="
/hpc/home/emt70/micromamba/envs/esmc/bin/python -u evaluate.py \
    --run-dir "$OUT_DIR" \
    --data-dir "$REPO/data/curated/d1_ppi"

echo "End: $(date -Iseconds)"
