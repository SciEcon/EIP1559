# Download the replication data on Harvard Dataverse
[Replication Data for: "Empirical Analysis of EIP-1559: Transaction Fees, Waiting Time, and Consensus Security"](https://doi.org/10.7910/DVN/K7UYPI)


# Raw data & code

This repository holds the raw data and the scripts for data processing.

## Summary

- Waiting time (Section 5.3): Folder `blockdata/` contains waiting time data in `blockdata.npy` and `waitingtime_csv.csv`.
- Network spikes (Table 4 & Figure 10): Folder `spikedata/` contains the data of network spikes.
- Miner's revenue (Figure 11 & 12): Folder `MEVdata/` contains data used for MEV analysis. Folder `MEVfig/` contains a detailed `MEVdata.csv` file and the figures.

## Reproducing data & graphs

### Raw mempool data

Raw mempool data used to calculate waiting time can be downloaded [here (about 20GB)](https://eip-1559-waiting-time-data.s3.us-west-002.backblazeb2.com/rawdata.tar.gz). After downloading it you should create a folder named `compressed/` to store the uncompressed raw data.

You can see several ``.txt`` files, containing the timestamp of transactions received by a particular full node. For example, the file ``LA_[2021070100,2021071600)_compressed.txt`` contains timestamp collected by our full node in LA between July 1, 2021 and July 16, 2021. Each line of these files describes a transaction. E.g., the following line means that transaction ``0x16...`` is received at Unix timestamp ``1626418821.870``.

```
0x16d1f71ef96c9456dc465ee2ce4d106b0dda0d440380c1cdd053c9deb58d8284 1626418821.870
```


### `blockdata/`

The script ``waitingtime.py`` processes the raw data and generates two files: the block information database `blockdetail.npy`, and a detailed transaction waiting time table. Outputs are stored in the `blockdata/` folder.

In the same folder there are three other files `gas_csv.csv`, `timestamp_csv.csv` and `sibling_csv.csv`, recording the gas usage, timestamp, and sibling count of the blocks respectively, derived from the Ethereum blockchain. These files are used to analyze network spikes in the paper.

### `spikedata/`

The script `spike.py` reads  `gas_csv.csv`, `timestamp_csv.csv`, and `sibling_csv.csv` in `blockdata/` and outputs `avggas.csv` (in `spikedata/` folder). The file `avggas.csv` tells the average gas per second around each block. From this file, we can obtain Figure 10 and Table 4.

### ``MEVdata/``

`MEVdata` contains the dataset for miner revenue, including Flashbots revenue collected from the Flashbots API, as well as other sources of rewards (including block rewards, uncle rewards, etc).

To reproduce the data, you can use the following command.

```bash
./mev.py --data
```

When executing the `--data` command, `mev.py` will call the Flashbots API, combining data from Ethereum full nodes (via `web3_api.py`) to generate MEV raw data. This data will be saved in the `MEVdata/` folder.

### ``MEVfig/``

The script ``mev.py`` plots data in ``MEVdata/``. The figures (figure 11 and figure 12 of our paper) are saved in the ``MEVfig/`` folder. To reproduce the figure, you can use the following command.

```bash
./mev.py --csv
./mev.py --img
```

Specifically, the first command will read the MEV raw data in the `MEVdata` folder and output a table `MEVfig/MEVdata.csv` with all the data.
The second command will to draw figures using `MEVfig/MEVdata.csv`.
