# hictools

hictools is a collection of handful tools for processing hic data based on:

- `nextflow` [<sup>1</sup>](#1) `pairtools` [<sup>2</sup>](#2) `cooler` [<sup>3</sup>](#3) `higlass` [<sup>4</sup>](#4) `......`

Currently, hictools is mainly composed of 3 parts:

- A `nextflow` based hic-data processing `pipeline`.
- Python `api` for handling outputs of the pipeline(`.cool`).
- A simple yet user friendly `higlass server`.


# Installation


```bash
conda install cooler pybigwig nginx
git clone https://github.com/zhqu1148980644/hictools.git
cd hictools && python setup.py install
```

`OR`

```bash
git clone https://github.com/zhqu1148980644/hictools.git
cd hictools && conda env create -f environment.yml
conda activate hictools
python setup.py install
```


# Usage

## Pipeline

- #####  Fill in the config file and run.

 Fill in a config file in order to  specify the desired sample files(.fastq) to process.
You can find a template config file in the current folder named `config_template.yml` after you executed this command:

```bash
nextflow run zhqu1148980644/hictools
```

- ##### Run the pipeline with this config file.

```bash
nextflow run -params-file config_template.yml hictools -resume \
-profile standard
# Choose the cluster profile if you wish to run in a another executor(platform) by using:
# -profile cluster
```
 
- ##### Outputs

You can find output folders after the execution of pipeline finished in the same directory as the current config file.

```bash
work/         # Working directory generated by nextflow.
log/          # Logging file generated by nextflow.
results/      # Main folder containing results of this pipeline.
    fastqc/ bams/ pairs/ cools/ features/ other/
```

***

## Visualize

- ##### Start a api server to provide tilesets

Files added into this folder will be automatically recorded and converted using `clodius`.

e.g. `.mcool` `.bam` `.bigwig` `.bed` ....

```bash
hictools hgserver serve ./work --num_worker 5
>>
Monitering folders:
        /store/home/user/path_you_run_pipeline/work
Openning api server: http://218.199.68.184:4321/api/v1
```

- ##### Start higlass web app and visit in browser

```bash
hictools hgserver view
>>
Go visit http://199.455.554.1:4567 in browser.
```

***

## CLI

```bash
hictools
>>
  compartments  Tools for topological associated domain analysis.
  expected      Compute expected values from a .cool file.
  hgserver      View results with higlass.
  peaks         Call peaks(loops) by using hiccups or cloops methods.
  tads          Tools for topological associated domain analysis.
```

***

## API

Check source code `api.py` for details.

---

## Notes

> `nextflow` is a pipeline framework based on the dataflow programing model, which can be spectacularly expressive when writing complex distributed pipelines.

> Pipeline built by `Nextflow` can be executed in multi platforms including SGE, LSF, SLURM, PBS, HTCondor batch schedulers , Kubernetes and Amazon AWS cloud platform by changing the executor specified in `~/.nextflow/assets/zhqu1148980644/hictools/nextflow.config`. The default executor is `SGE`(Sun Grid Engine). You may need to change it depending on the platform you use.

> The pipeline procesures in hictools are similar to that of the `Hi-C Processing Pipeline` used by `4DN`.

 ## Reference

- [nextflow](https://github.com/nextflow-io/nextflow "nextflow") A DSL for data-driven computational pipelines. <a class="anchor" id="1"></a>

- [pairtools](https://github.com/mirnylab/cooler "pairtools") A cool place to store your Hi-C. <a class="anchor" id="2"></a>

- [cooler](https://github.com/mirnylab/pairtools "cooler") CLI tools to process mapped Hi-C data. <a class="anchor" id="3"></a>

- [higlass](https://github.com/higlass/higlass "higlass") Fast large scale matrix visualization for the web. <a class="anchor" id="4"></a>
