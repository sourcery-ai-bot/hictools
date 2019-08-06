# hictools
hictools is a collection of handful tools for processing hic data.
Currently, hictools is mainly composed of two parts:
- A `nextflow` based hic-data processing pipeline with procedures similar to that of the Hi-C Processing Pipeline used by 4DN.
- Python scripts for handling outputs of the pipeline(`.cool`).
> `nextflow` is a pipeline framework based on the dataflow 
programing model, which can be spectacularly expressive when writing 
complex distributed pipelines.

# Installation
```bash
conda install -c bioconda nextflow
nextflow run zhqu1148980644/hictools
```

### Update
```bash
nextflow drop -f zhqu1148980644/hictools
nextflow run zhqu1148980644/hictools
```
# Usage
## Pipeline
- ###### Fill in the config file.

In general, you need to fill in a config file in order to 
specify the desired sample files(.fastq) to process.
You can find a template config file in the current folder named `config_template.yml` after you executed this command:
```bash
nextflow run zhqu1148980644/hictools
```
`config_template.yml`:
```yaml
# There are 3 levels through which you can organize your input data.
raw_reads:
    sample1:
        bio1:
            - 'x06_1.fastq'
            - 'x06_2.fastq'
        bio2:
            - 'https://url....lane1_1.fastq.gz'
            - 'lane1_2.fastq'
            - 'lane[4,5,6]*fastq'
            - 'lane10*'
    sample2:
        bio1:
            - 'SRR2601843'
            - 'x07_1.fastq'
            - 'x07_2.fastq'
```
As you can see, with the help of `glob`, `URL` and `SRR number`,
filling in this file can be quite easy without massive annoying typing.

In practice, more parameters should be specified depending on
the corresponding types of hic experiments. See detailed description of each
parameter in `config_template.yml`.
- ###### Run the pipeline with the config file.

1. Run in local.
```bash
nextflow run -params-file config_template.yml -profile standard hictools -resume
```
2. Run in cluster(default is SGE).
```bash
nextflow run -params-file config_template.yml -profile cluster hictools -resume
```
> Pipeline built by `Nextflow` can be executed in multi platforms including 
SGE, LSF, SLURM, PBS, HTCondor batch schedulers , Kubernetes and
 Amazon AWS cloud platform by changing the executor specified in `nextflow.config`.

> The default executor is SGE(Sun Grid Engine). You may need to change it 
depending on the platform you use.
 
# Outputs
You can find output folders after the execution of pipeline finished in the same directory as the current config file.
```bash
results      # Main folder containing results of thi pipeline. 
log          # Logging file generated by nextflow which is useful for fine tunning the nextflow.config file.
work         # Working directory generated by nextflow.
```
##### Interpretation of subfolder in `results`
- `results/fastqc`    QC results generated by running `fasqc` and `multiqc`.
- `results/bams`      Mapping results of each pair of fastq file generated by `bwa`.
- `results/pairs`     Contact pairs in .pair format and basic statistical info generated by `pairtools`.
- `results/cools`     HDF5 based .cool file containing contact matrix of hic experiment generated by `cooler`.
- `results/features`  Normal features of a hic contact matrix. i.e. loops, insulation score, di score, tad, decay, compartment.
- `results/other`     Downloaded files, fastq/bam/pair chunks, sra-dumped fastqs and enzyme-digested .bed file. 
## 
