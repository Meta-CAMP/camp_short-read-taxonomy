# Short-Read Taxonomy

[![Documentation Status](https://img.shields.io/badge/docs-passing-brightgreen.svg)](https://camp-documentation.readthedocs.io/en/latest/shortreadtax/index.html) ![Version](https://img.shields.io/badge/version-0.8.1-brightgreen)

<!-- [![Documentation Status](https://img.shields.io/readthedocs/camp_short-read-taxonomy)](https://camp-documentation.readthedocs.io/en/latest/short-read-taxonomy.html) -->

## Overview

This module is designed to function as both a standalone short-read-taxonomic classification pipeline as well as a component of the larger CAMP metagenome analysis pipeline. As such, it is both self-contained (ex. instructions included for the setup of a versioned environment, etc.), and seamlessly compatible with other CAMP modules (ex. ingests and spawns standardized input/output config files, etc.). 

There are three taxonomic classification tools integrated which can be run in any combination: MetaPhlAn4, Kraken2 (along with Bracken for relative abundance estimation), and XTree (formerly UTree). 

## Installation

> [!TIP]
> All databases used in CAMP modules will also be available for download on Zenodo (link TBD).

1. Clone repo from [Github](<https://github.com/Meta-CAMP/camp_short-read-taxonomy>).
```Bash
git clone https://github.com/Meta-CAMP/camp_short-read-taxonomy
```

2. Set up the conda environment (contains Snakemake, Click, and other essentials) using `configs/conda/short_read_taxonomy.yaml`. 

If you don't already have `conda` handy, we recommend installing `miniforge`, which is a minimal conda installer that, by default, installs packages from open-source community-driven channels such as `conda-forge`.
```Bash
# If you don't already have conda on your system...
# wget https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh

# Create and activate conda environment 
cd camp_short-read-taxonomy
conda env create -f configs/conda/short_read_taxonomy.yaml
conda activate short_read_taxonomy
```

3. `bbmap` needs to be installed directly from SourceForge with the following commands. After installation, the location of the executable (called `bbmap/bbmask.sh`) needs to be added to `test_data/parameters.yaml` and `configs/parameters.yaml` under `bbmask_scr`.
```Bash
https://sourceforge.net/projects/bbmap/files/latest/download
tar -xzf download
```

4. XTree also needs to be installed from Github directly with the following commands. After installation, the location of the executable (called `UTree/xtree`, needs to `chmod`-ed) needs to be added to `test_data/parameters.yaml` and `configs/parameters.yaml` under `xtree_executable`.
```Bash
git clone https://github.com/GabeAl/UTree
```

5. Download the databases for the taxonomic pipelines you want to use. Be sure to update the locations of the databases in the `parameters.yaml` file. This may take a few hours.
* Note: If you want to speed up the download process, trying installing `axel` and replacing the wget with `axel -a`!

6. For MetaPhlAn4:
```Bash
wget https://s3.us-east-1.wasabisys.com/camp-databases/v0.1.1/taxonomy/metaphlan_20220926.tar.gz
tar -zxvf metaphlan_20220926.tar.gz

# An alternate option for automatic installation using the MetaPhlAn4 command
metaphlan --install --bowtie2db /path/to/database_dir
```

7. For Kraken2:
    - The NCBI Taxonomy database's pairing of names to accession IDs was downloaded along with the Kraken2 database. It can be found at ``/path/to/Databases/Kraken2/taxonomy/names.dmp``.
    - Note: The Kraken2 database hosted at Wasabi is currently incomplete. Please use the database download command from Kraken2's Github
```Bash
# wget https://s3.us-east-1.wasabisys.com/camp-databases/v0.1.1/taxonomy/Kraken2.tar.gz
# tar -zxvf Kraken2.tar.gz
/path/to/bin/kraken2/kraken2-build --standard --threads 40 --db /path/to/Databases/Kraken2_10182023
```

8. For xtree:
    - Note: The xtree database hosted at Wasabi is currently incomplete. Download details TBD.
```Bash
# wget https://s3.us-east-1.wasabisys.com/camp-databases/v0.1.1/orfcalling/xtree_db_gtdb207_kmer29_comp2_20220722.tar.gz
# tar -zxvf xtree_db_gtdb207_kmer29_comp2_20220722.tar.gz
```

9. Update the locations of the test datasets in `test_data/samples.csv`, and the relevant parameters in `test_data/parameters` and `test_data/resources.yaml`.

10. Make sure the installed pipeline works correctly. With 40 threads and a maximum of 150 GB allocated for a command (`xtree`), the test dataset should finish in approximately 38 minutes.
```Bash
python /path/to/camp_short-read-taxonomy/workflow/short-read-taxonomy.py test
```

## Using the Module

**Input**: `/path/to/samples.csv` provided by the user.

**Output**: Summary reports from MetaPhlAn4, Kraken2, and/or XTree. For more information, see the demo test output directory in `test_data/test_out`. 

- `/path/to/work/dir/short-read-taxonomy/final_reports/T_R.csv`: Taxa found by tool T at rank R across all samples

- `/path/to/work/dir/short-read-taxonomy/final_reports/unclassified/T/*.fastq.gz`: Short reads that were marked as unclassified by tool T

### Module Structure

```
└── workflow
    ├── Snakefile
    ├── short-read-taxonomy.py
    ├── utils.py
    ├── __init__.py
    └── ext/
        └── scripts/
```
- `workflow/short-read-taxonomy.py`: Click-based CLI that wraps the `snakemake` and unit test generation commands for clean management of parameters, resources, and environment variables.
- `workflow/Snakefile`: The `snakemake` pipeline. 
- `workflow/utils.py`: Sample ingestion and work directory setup functions, and other utility functions used in the pipeline and the CLI.
- `ext/`: External programs, scripts, and small auxiliary files that are not conda-compatible but used in the workflow.

### Running the Workflow

1. Make your own `samples.csv` based on the template in `configs/samples.csv`. Sample test data can be found in `test_data/`.
    - `samples.csv` requires either absolute paths or paths relative to the directory that the module is being run in
    - Note: MetaPhlAn4 and Bracken merge outputs from all samples to get aggregated relative abundances across all samples. To get relative abundances for a single sample, put each sample in its own `samples.csv`.

2. Update the relevant parameters in `configs/parameters.yaml`.

3. Update the computational resources available to the pipeline in `configs/resources.yaml`. 

#### Command Line Deployment

To run CAMP on the command line, use the following, where `/path/to/work/dir` is replaced with the absolute path of your chosen working directory, and `/path/to/samples.csv` is replaced with your copy of `samples.csv`. 
    - The default number of cores available to Snakemake is 1 which is enough for test data, but should probably be adjusted to 10+ for a real dataset.
    - Relative or absolute paths to the Snakefile and/or the working directory (if you're running elsewhere) are accepted!
```Bash
python /path/to/camp_short-read-taxonomy/workflow/short-read-taxonomy.py \
    (-c number_of_cores_allocated) \
    (-p /path/to/parameters.yaml) \
    (-r /path/to/resources.yaml) \
    -d /path/to/work/dir \
    -s /path/to/samples.csv
```

#### Slurm Cluster Deployment

To run CAMP on a job submission cluster (for now, only Slurm is supported), use the following.
    - `--slurm` is an optional flag that submits all rules in the Snakemake pipeline as `sbatch` jobs. 
    - In Slurm mode, the `-c` flag refers to the maximum number of `sbatch` jobs submitted in parallel, **not** the pool of cores available to run the jobs. Each job will request the number of cores specified by threads in `configs/resources/slurm.yaml`.
```Bash
sbatch -J jobname -o jobname.log << "EOF"
#!/bin/bash
python /path/to/camp_short-read-taxonomy/workflow/short-read-taxonomy.py 
    --slurm \
    (-c max_number_of_parallel_jobs_submitted) \
    (-p /path/to/parameters.yaml) \
    (-r /path/to/resources.yaml) \
    -d /path/to/work/dir \
    -s /path/to/samples.csv
EOF
```

#### Finishing Up

1. To plot grouped bar graph(s) of the sample alpha and beta diversities remaining after each quality control step in each sample, set up the dataviz environment and follow the instructions in the Jupyter notebook:
```Bash
conda env create -f configs/conda/dataviz.yaml
conda activate dataviz
jupyter notebook &
```

2. After checking over `final_reports/` and making sure you have everything you need, you can delete all intermediate files to save space. 
```Bash
python /path/to/camp_short-read-taxonomy/workflow/short-read-taxonomy.py cleanup \
    -d /path/to/work/dir \
    -s /path/to/samples.csv
```

3. If for some reason the module keeps failing, CAMP can print a script containing all of the remaining commands that can be run manually. 
```Bash
python /path/to/camp_short-read-taxonomy/workflow/short-read-taxonomy.py --dry_run \
    -d /path/to/work/dir \
    -s /path/to/samples.csv
```

## Credits

- This package was created with [Cookiecutter](https://github.com/cookiecutter/cookiecutter>) as a simplified version of the [project template](https://github.com/audreyr/cookiecutter-pypackage>).
- Free software: MIT
